"""Thin OpenAI-compatible LLM client.

Works with any endpoint that speaks the OpenAI Chat Completions schema:
- OpenAI (`https://api.openai.com/v1`)
- Anthropic via OpenAI-compat proxies (e.g. router endpoints)
- Local servers (vllm, llama.cpp server, ollama with OpenAI shim)

The endpoint, key, and model are read from environment variables:
- `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`
- Falls back to `OPENAI_API_KEY` + `https://api.openai.com/v1` if those are unset.
"""
from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from typing import Any

from openai import OpenAI

from app.config import settings

log = logging.getLogger(__name__)


class LLMUnavailableError(RuntimeError):
    """Raised when callers ask for an LLM completion but no key is configured."""


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    if not settings.has_llm:
        raise LLMUnavailableError(
            "No LLM key configured. Set LLM_API_KEY (and LLM_BASE_URL) or OPENAI_API_KEY."
        )
    return OpenAI(
        api_key=settings.effective_api_key,
        base_url=settings.effective_base_url,
        timeout=settings.llm_timeout_sec,
        # Some OpenAI-compatible proxies (Cloudflare-fronted ones in particular)
        # block the SDK's default ``OpenAI/Python`` UA. Pin a plain UA + drop the
        # vendor-specific x-stainless-* headers so the proxy treats us like curl.
        default_headers={
            "User-Agent": "ai-music-backend/0.1 (+httpx)",
        },
    )


def chat(
    *,
    system: str,
    user: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
    model: str | None = None,
    response_format: dict[str, str] | None = None,
) -> str:
    """Run one chat completion and return the assistant message text.

    Strips out reasoning blocks (``<think>...</think>``) some routers prepend.
    """
    client = _client()
    kwargs: dict[str, Any] = dict(
        model=model or settings.effective_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature if temperature is not None else settings.llm_temperature,
        max_tokens=max_tokens or settings.llm_max_tokens,
    )
    if response_format is not None:
        kwargs["response_format"] = response_format
    # Use streaming so Cloudflare-fronted endpoints (100s 524 timeout) keep the
    # connection alive while the model thinks. We accumulate chunks and return
    # the full text — callers don't need to know it streamed.
    kwargs["stream"] = True
    parts: list[str] = []
    stream = client.chat.completions.create(**kwargs)
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        piece = getattr(delta, "content", None)
        if piece:
            parts.append(piece)
    text = "".join(parts).strip()
    return _strip_reasoning(text)


def chat_json(
    *,
    system: str,
    user: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Run a chat completion expected to return a single JSON object.

    Strategy (best-effort, in order):
    1. Ask for ``response_format={"type": "json_object"}`` — endpoints that
       support it will guarantee valid JSON. If the endpoint rejects the
       parameter, fall back to plain mode.
    2. Parse the response with :func:`_extract_json`, which tolerates
       fenced blocks, prose preambles, trailing commas, and unescaped
       newlines inside strings.
    3. On parse failure, retry **once** with the previous (broken) output
       and the parser's complaint appended to the user prompt — most models
       fix the JSON when shown what was wrong.

    Raises ``ValueError`` if both attempts fail.
    """
    strict_system = (
        system
        + "\n\nYou MUST reply with a SINGLE valid JSON object and nothing else."
        + " Do not wrap it in markdown fences. Do not add commentary before or after."
        + " Inside string values, never include unescaped newlines or unescaped double quotes —"
        + ' use \\n for newlines and \\" for embedded quotes.'
    )
    raw = _chat_with_optional_json_mode(
        system=strict_system,
        user=user,
        temperature=temperature,
        max_tokens=max_tokens,
        model=model,
    )
    try:
        return _extract_json(raw)
    except ValueError as first_exc:
        log.warning("LLM JSON parse failed on first attempt: %s", first_exc)
        retry_user = (
            user
            + "\n\n[Retry] Your previous response was not valid JSON."
            + f" Parser error: {first_exc!s}.\n"
            + "Reply again with ONLY a valid JSON object. No commentary, no markdown."
        )
        raw = _chat_with_optional_json_mode(
            system=strict_system,
            user=retry_user,
            temperature=0.2,  # tighter sampling on retry
            max_tokens=max_tokens,
            model=model,
        )
        return _extract_json(raw)


def _chat_with_optional_json_mode(
    *,
    system: str,
    user: str,
    temperature: float | None,
    max_tokens: int | None,
    model: str | None,
) -> str:
    """Try ``response_format=json_object`` first; fall back if the server rejects it."""
    try:
        return chat(
            system=system,
            user=user,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
            response_format={"type": "json_object"},
        )
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).lower()
        if "response_format" in msg or "json_object" in msg or "unsupported" in msg:
            log.info("Endpoint does not support response_format=json_object; retrying without")
            return chat(
                system=system,
                user=user,
                temperature=temperature,
                max_tokens=max_tokens,
                model=model,
            )
        raise


# ---------- Helpers ----------


_THINK_RE = re.compile(r"<think>.*?</think>", flags=re.DOTALL | re.IGNORECASE)
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", flags=re.DOTALL | re.IGNORECASE)


def _strip_reasoning(text: str) -> str:
    return _THINK_RE.sub("", text).strip()


def _extract_json(text: str) -> dict[str, Any]:
    text = _strip_reasoning(text)
    candidates: list[str] = []
    # Try fenced block first.
    m = _FENCE_RE.search(text)
    if m:
        candidates.append(m.group(1).strip())
    # Then the first balanced {...} block.
    balanced = _balanced_braces(text)
    if balanced is not None:
        candidates.append(balanced)

    if not candidates:
        raise ValueError(f"No JSON object found in LLM output: {text[:200]}")

    last_exc: Exception | None = None
    for candidate in candidates:
        for attempt in (candidate, _repair_json(candidate)):
            try:
                return json.loads(attempt)
            except json.JSONDecodeError as exc:
                last_exc = exc
                continue
    raise ValueError(
        f"Invalid JSON from LLM ({last_exc}): {candidates[-1][:400]}"
    ) from last_exc


def _balanced_braces(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i, ch in enumerate(text[start:], start=start):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


_TRAILING_COMMA_RE = re.compile(r",(\s*[\}\]])")


def _repair_json(text: str) -> str:
    """Attempt small fixups for common LLM JSON mistakes.

    - Strip trailing commas before ``}`` / ``]``.
    - Replace smart quotes (``“ ”``) with straight quotes.
    - Escape literal newlines inside string values.
    """
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = _TRAILING_COMMA_RE.sub(r"\1", text)
    out: list[str] = []
    in_string = False
    escape = False
    for ch in text:
        if escape:
            out.append(ch)
            escape = False
            continue
        if ch == "\\" and in_string:
            out.append(ch)
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            out.append(ch)
            continue
        if in_string and ch == "\n":
            out.append("\\n")
            continue
        if in_string and ch == "\r":
            out.append("\\r")
            continue
        if in_string and ch == "\t":
            out.append("\\t")
            continue
        out.append(ch)
    return "".join(out)
