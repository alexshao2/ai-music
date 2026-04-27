"""Unit tests for the LLM client's max_tokens truncation handling.

The council's Lyricist / Arranger personas emit large JSON blobs. When the
endpoint truncates the completion (``finish_reason=length``), the resulting
partial string is almost never parseable — historically we'd surface this as a
generic "No JSON object found" error, which the council retry loop couldn't
distinguish from malformed JSON. On the second truncation the persona would
give up and fall back to the deterministic stub, leaving the user with
placeholder lyrics ("[chờ Lyricist tinh chỉnh]") and no indication why.

These tests pin the new behaviour: ``chat()`` raises
:class:`LLMResponseTruncatedError`, and ``chat_json()`` retries with extra
headroom instead of returning a broken JSON.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.config import settings
from app.services import llm as llm_svc
from app.services.llm import LLMResponseTruncatedError


class _FakeChunk:
    def __init__(self, content: str | None, finish_reason: str | None = None) -> None:
        delta = SimpleNamespace(content=content)
        self.choices = [SimpleNamespace(delta=delta, finish_reason=finish_reason)]


def _fake_stream(pieces: list[str], finish_reason: str) -> list[_FakeChunk]:
    chunks = [_FakeChunk(p) for p in pieces]
    chunks.append(_FakeChunk(None, finish_reason=finish_reason))
    return chunks


@pytest.fixture(autouse=True)
def _fake_llm_creds():
    """Give the LLM client valid-looking creds so `_client()` doesn't raise."""
    original = (settings.llm_api_key, settings.llm_base_url)
    settings.llm_api_key = "test-key"
    settings.llm_base_url = "https://example.test/v1"
    llm_svc._client.cache_clear()
    try:
        yield
    finally:
        settings.llm_api_key, settings.llm_base_url = original
        llm_svc._client.cache_clear()


def test_chat_raises_on_finish_reason_length() -> None:
    """When the API reports finish_reason='length', chat() must raise."""
    fake_stream = _fake_stream(["{\"title\":\"Ngày ", "qua m"], finish_reason="length")

    class _FakeClient:
        class chat:  # noqa: N801
            class completions:  # noqa: N801
                @staticmethod
                def create(**_kwargs):
                    return iter(fake_stream)

    with patch.object(llm_svc, "_client", return_value=_FakeClient()):
        with pytest.raises(LLMResponseTruncatedError) as exc_info:
            llm_svc.chat(system="sys", user="usr")
    # Partial output preserved on the exception for logging.
    assert "Ngày" in exc_info.value.partial


def test_chat_json_retries_with_larger_budget_after_truncation() -> None:
    """chat_json() must retry on truncation with ≥ original max_tokens."""
    full_json = json.dumps({"message": "ok", "contributions": {"lyrics": {"v1": "x"}}})
    calls: list[dict] = []

    def _fake_chat(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise LLMResponseTruncatedError("{\"message\": \"truncated mid-")
        return full_json

    with patch.object(llm_svc, "chat", side_effect=_fake_chat):
        out = llm_svc.chat_json(system="sys", user="usr", max_tokens=2000)
    assert out == {"message": "ok", "contributions": {"lyrics": {"v1": "x"}}}
    assert len(calls) == 2, "Expected exactly one retry after truncation"
    # Retry budget must be strictly larger than the first attempt's.
    assert calls[1]["max_tokens"] >= calls[0]["max_tokens"]
    assert calls[1]["max_tokens"] > 2000


def test_chat_json_retry_budget_capped() -> None:
    """Retry budget must not exceed the hard cap (8000)."""
    full_json = json.dumps({"ok": True})
    calls: list[dict] = []

    def _fake_chat(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise LLMResponseTruncatedError("partial")
        return full_json

    with patch.object(llm_svc, "chat", side_effect=_fake_chat):
        llm_svc.chat_json(system="sys", user="usr", max_tokens=7000)
    assert calls[1]["max_tokens"] <= 8000


def test_default_max_tokens_fits_lyricist_schema() -> None:
    """Sanity check: the default LLM_MAX_TOKENS is large enough for Lyricist.

    The Lyricist persona outputs a single JSON with two full lyrics blocks
    (verse_1, pre_chorus, chorus, verse_2, bridge × plain + markers) plus
    prosody notes and imagery. Setting this below ~3000 tokens silently
    truncates VN output. We pin the default here so a future refactor that
    accidentally lowers the default fails this test instead of silently
    regressing the draft.
    """
    assert settings.llm_max_tokens >= 4000
