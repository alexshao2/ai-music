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
) -> str:
    """Run one chat completion and return the assistant message text.

    Strips out reasoning blocks (``<think>...</think>``) some routers prepend.
    """
    client = _client()
    resp = client.chat.completions.create(
        model=model or settings.effective_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature if temperature is not None else settings.llm_temperature,
        max_tokens=max_tokens or settings.llm_max_tokens,
        stream=False,
    )
    text = (resp.choices[0].message.content or "").strip()
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

    Robust against:
    - Models that wrap output in ```json fences.
    - Routers that prepend a reasoning preamble.
    - Trailing prose after the JSON object.
    """
    raw = chat(
        system=system + "\n\nYou MUST reply with a single valid JSON object and nothing else.",
        user=user,
        temperature=temperature,
        max_tokens=max_tokens,
        model=model,
    )
    return _extract_json(raw)


# ---------- Helpers ----------


_THINK_RE = re.compile(r"<think>.*?</think>", flags=re.DOTALL | re.IGNORECASE)
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", flags=re.DOTALL | re.IGNORECASE)


def _strip_reasoning(text: str) -> str:
    return _THINK_RE.sub("", text).strip()


def _extract_json(text: str) -> dict[str, Any]:
    text = _strip_reasoning(text)
    # Try fenced block first.
    m = _FENCE_RE.search(text)
    if m:
        candidate = m.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    # Fall back to first {...} balanced object.
    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found in LLM output: {text[:200]}")
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON from LLM ({exc}): {candidate[:300]}"
                    ) from exc
    raise ValueError(f"Unterminated JSON in LLM output: {text[:300]}")
