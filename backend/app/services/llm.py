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

import contextlib
import json
import logging
import re
import time
from functools import lru_cache
from typing import Any

import httpx
from openai import OpenAI

from app.config import settings

log = logging.getLogger(__name__)


class LLMUnavailableError(RuntimeError):
    """Raised when callers ask for an LLM completion but no key is configured."""


class LLMStreamStalledError(TimeoutError):
    """Raised when the streaming LLM connection sends nothing for a while.

    Distinct from :class:`httpx.ReadTimeout` because we want the persona
    retry loop in ``council.py`` to surface this as a stalled-stream
    diagnostic ("network seems silent") rather than a generic timeout.
    Both are caught by the bare ``except Exception`` in
    ``_run_persona_with_retry`` so retry behaviour is identical — this
    is purely about logging clarity.
    """

    def __init__(self, idle_seconds: float, partial_chars: int) -> None:
        super().__init__(
            f"LLM stream silent for {idle_seconds:.1f}s "
            f"(received {partial_chars} chars before stall). "
            "Network or upstream LLM may be hung; retrying."
        )
        self.idle_seconds = idle_seconds
        self.partial_chars = partial_chars


class LLMTotalBudgetExceededError(TimeoutError):
    """Raised when a single streaming completion exceeds ``llm_timeout_sec``.

    Catches the case where each individual chunk arrives just under
    ``llm_read_timeout_sec`` (so the per-chunk idle guard never trips)
    but the total wall-clock duration of the call grows unbounded. A
    healthy model finishes in well under the total budget; sustained
    near-idle streaming is indistinguishable from a hang for the user.
    """

    def __init__(self, elapsed_seconds: float, partial_chars: int) -> None:
        super().__init__(
            f"LLM stream exceeded total budget after {elapsed_seconds:.1f}s "
            f"(received {partial_chars} chars). "
            "Upstream LLM is too slow; retrying."
        )
        self.elapsed_seconds = elapsed_seconds
        self.partial_chars = partial_chars


class LLMResponseTruncatedError(ValueError):
    """Raised when the model hit ``max_tokens`` before finishing its response.

    The partial text is attached so callers can still inspect/log it, but a
    truncated JSON object is virtually never parseable, so we surface this as
    an explicit parse-style failure that :func:`chat_json`'s retry loop can
    distinguish from merely malformed output.
    """

    def __init__(self, partial: str) -> None:
        super().__init__(
            "LLM response truncated at max_tokens (finish_reason=length). "
            "Bump LLM_MAX_TOKENS or shorten the prompt."
        )
        self.partial = partial


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    if not settings.has_llm:
        raise LLMUnavailableError(
            "No LLM key configured. Set LLM_API_KEY (and LLM_BASE_URL) or OPENAI_API_KEY."
        )
    # Use granular httpx.Timeout so a stalled TCP connection fails fast
    # instead of waiting the full ``llm_timeout_sec`` (180s by default).
    # ``connect`` is short (the LLM endpoint is either reachable in
    # seconds or we want to retry); ``read`` caps the wait for a single
    # chunk. ``write`` and ``pool`` are left unset and inherit the
    # ``timeout=`` scalar — IMPORTANT: ``httpx.Timeout`` ignores the
    # scalar entirely when all four sub-timeouts are explicit, so we
    # must leave at least one unset for ``llm_timeout_sec`` to remain
    # meaningful as a fallback. The total wall-clock budget for the
    # streaming response is enforced separately in :func:`chat`.
    timeout = httpx.Timeout(
        timeout=settings.llm_timeout_sec,
        connect=settings.llm_connect_timeout_sec,
        read=settings.llm_read_timeout_sec,
    )
    return OpenAI(
        api_key=settings.effective_api_key,
        base_url=settings.effective_base_url,
        timeout=timeout,
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
    finish_reason: str | None = None
    idle_budget = float(settings.llm_read_timeout_sec)
    total_budget = float(settings.llm_timeout_sec)
    stream = client.chat.completions.create(**kwargs)
    started_at = time.monotonic()
    last_chunk_at = started_at
    try:
        for chunk in stream:
            now = time.monotonic()
            # Idle-budget guard: even if httpx hasn't surfaced a read
            # timeout (e.g. proxy keeping the TCP connection warm with
            # zero-length frames), refuse to wait forever for actual
            # content. The persona retry loop will substitute a stub or
            # rerun the call.
            if now - last_chunk_at > idle_budget:
                idle_for = now - last_chunk_at
                with contextlib.suppress(Exception):
                    stream.response.close()  # type: ignore[attr-defined]
                raise LLMStreamStalledError(
                    idle_seconds=idle_for,
                    partial_chars=sum(len(p) for p in parts),
                )
            # Total-budget guard: a model that dribbles one chunk every
            # ``idle_budget - epsilon`` seconds would never trip the
            # idle guard but could stream for hours. Cap each call at
            # ``llm_timeout_sec`` overall so the user sees a bounded
            # worst-case wait time.
            if now - started_at > total_budget:
                elapsed = now - started_at
                with contextlib.suppress(Exception):
                    stream.response.close()  # type: ignore[attr-defined]
                raise LLMTotalBudgetExceededError(
                    elapsed_seconds=elapsed,
                    partial_chars=sum(len(p) for p in parts),
                )
            # Only "real" chunks reset the idle timer. Some proxies emit
            # empty SSE events (``{"choices": []}``) as TCP keepalives —
            # if we treated those as fresh content the idle guard above
            # would never fire and the user would wait the full
            # ``llm_timeout_sec`` instead of ``llm_read_timeout_sec``.
            if not chunk.choices:
                continue
            last_chunk_at = now
            choice = chunk.choices[0]
            delta = choice.delta
            piece = getattr(delta, "content", None)
            if piece:
                parts.append(piece)
            # OpenAI-compat streams surface the final stop reason only on the
            # last chunk; everything before it is None. Keep the last non-None.
            this_reason = getattr(choice, "finish_reason", None)
            if this_reason:
                finish_reason = this_reason
    finally:
        # Ensure the underlying HTTP response is released even if the
        # iterator raised mid-flight; the openai sdk's stream wraps a
        # context manager, but we acquired it with ``create()`` so we
        # close it ourselves to avoid leaking sockets on error paths.
        with contextlib.suppress(Exception):
            stream.response.close()  # type: ignore[attr-defined]
    text = _strip_reasoning("".join(parts).strip())
    if finish_reason == "length":
        # Truncation is almost always catastrophic for JSON callers. Surface it
        # explicitly so the caller logs "max_tokens" rather than a mysterious
        # "No JSON object found in LLM output".
        log.warning(
            "LLM response truncated at max_tokens=%s (model=%s, len=%d chars)",
            kwargs.get("max_tokens"),
            kwargs.get("model"),
            len(text),
        )
        raise LLMResponseTruncatedError(text)
    return text


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
    try:
        raw = _chat_with_optional_json_mode(
            system=strict_system,
            user=user,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        )
    except LLMResponseTruncatedError as first_exc:
        # The first call hit max_tokens. Retry with a larger budget AND a
        # nudge to be more concise — otherwise the second call usually
        # truncates in the same place.
        first_exc_for_retry: Exception = first_exc
    else:
        try:
            return _extract_json(raw)
        except ValueError as first_exc:
            log.warning("LLM JSON parse failed on first attempt: %s", first_exc)
            first_exc_for_retry = first_exc

    retry_user = (
        user
        + "\n\n[Retry] Your previous response was not valid JSON."
        + f" Parser error: {first_exc_for_retry!s}.\n"
        + "Reply again with ONLY a valid JSON object. No commentary, no markdown."
        + " Keep every string value concise — do not pad with filler — so the"
        + " whole JSON fits in the token budget."
    )
    # Give the retry 50% more headroom (capped) when the first try ran out.
    retry_max = max_tokens or settings.llm_max_tokens
    if isinstance(first_exc_for_retry, LLMResponseTruncatedError):
        retry_max = min(int(retry_max * 1.5), 8000)
    raw = _chat_with_optional_json_mode(
        system=strict_system,
        user=retry_user,
        temperature=0.2,  # tighter sampling on retry
        max_tokens=retry_max,
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
