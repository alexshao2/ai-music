"""Tests for LLM client timeout / stalled-stream handling.

When the LLM endpoint stops sending chunks mid-completion (network drop,
proxy holding the TCP connection alive but no data, hung upstream),
historically the openai-python SDK would block until the SDK-level
``timeout`` value (default 180s in this repo). With 6 personas × 2
attempts per compose, that's 36+ minutes of "hang" before any persona
falls back to the stub.

These tests pin two protections:

1. ``_client()`` configures granular ``httpx.Timeout`` so connect/read
   timeouts can fail fast independently of the total budget.
2. ``chat()`` enforces an additional wall-clock idle budget BETWEEN
   stream chunks — a healthy completion sends data every few seconds,
   so a multi-minute silence is treated as a dead connection.
"""
from __future__ import annotations

import time
from collections.abc import Iterator
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

from app.config import settings
from app.services import llm as llm_svc
from app.services.llm import LLMStreamStalledError


class _FakeChunk:
    def __init__(self, content: str | None, finish_reason: str | None = None) -> None:
        delta = SimpleNamespace(content=content)
        self.choices = [SimpleNamespace(delta=delta, finish_reason=finish_reason)]


class _FakeStream:
    """Iterable stream with a closeable .response — mirrors openai sdk."""

    def __init__(self, chunks: list[_FakeChunk]) -> None:
        self._chunks = chunks
        self.closed = False

        # The real openai sdk exposes ``.response`` as the underlying
        # httpx response so callers can release the socket. We mimic
        # the surface we use.
        outer = self

        class _Resp:
            def close(self) -> None:
                outer.closed = True

        self.response = _Resp()

    def __iter__(self) -> Iterator[_FakeChunk]:
        yield from self._chunks


def _fake_client_returning(stream: _FakeStream) -> object:
    class _Client:
        class chat:  # noqa: N801
            class completions:  # noqa: N801
                @staticmethod
                def create(**_kwargs):
                    return stream

    return _Client()


@pytest.fixture(autouse=True)
def _fake_llm_creds():
    original = (settings.llm_api_key, settings.llm_base_url)
    settings.llm_api_key = "test-key"
    settings.llm_base_url = "https://example.test/v1"
    llm_svc._client.cache_clear()
    try:
        yield
    finally:
        settings.llm_api_key, settings.llm_base_url = original
        llm_svc._client.cache_clear()


# --- Granular timeout configuration --------------------------------------


def test_client_uses_granular_httpx_timeout() -> None:
    """``_client()`` must configure connect/read separately from total."""
    captured: dict[str, object] = {}

    def fake_openai_ctor(**kwargs: object) -> object:
        captured.update(kwargs)
        return SimpleNamespace()

    with patch.object(llm_svc, "OpenAI", side_effect=fake_openai_ctor):
        llm_svc._client.cache_clear()
        llm_svc._client()

    timeout = captured["timeout"]
    assert isinstance(timeout, httpx.Timeout)
    # Sanity: connect should be the dedicated short value, read should
    # be the dedicated stream-chunk value, both distinct from the total
    # budget.
    assert timeout.connect == pytest.approx(settings.llm_connect_timeout_sec)
    assert timeout.read == pytest.approx(settings.llm_read_timeout_sec)
    # Total budget is honoured but not used as the read timeout.
    assert timeout.read != pytest.approx(settings.llm_timeout_sec)


def test_default_timeout_values_are_sensible() -> None:
    """Pin defaults so a future refactor doesn't accidentally relax them."""
    assert settings.llm_connect_timeout_sec <= 30.0
    assert settings.llm_read_timeout_sec <= 120.0
    # Read timeout should remain comfortably below the total budget so
    # a stalled stream surfaces as a retryable error rather than the
    # caller-facing 3-minute hang.
    assert settings.llm_read_timeout_sec < settings.llm_timeout_sec


# --- Stalled-stream wall-clock guard -------------------------------------


def test_chat_raises_on_idle_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    """Long gap between chunks must surface as LLMStreamStalledError.

    We mock :func:`time.monotonic` to fast-forward by 999s between the
    first and second chunk so the wall-clock check trips even though
    the iterator yielded immediately.
    """
    chunks = [_FakeChunk("Once "), _FakeChunk("upon ")]
    fake_stream = _FakeStream(chunks)

    # Sequence: first call sets baseline (t=0); next call inside the
    # for-loop returns a value far past idle_budget so the guard fires.
    times = iter([0.0, 9999.0])

    def fake_monotonic() -> float:
        return next(times, 9999.0)

    monkeypatch.setattr(llm_svc.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(settings, "llm_read_timeout_sec", 60.0)

    with patch.object(llm_svc, "_client", return_value=_fake_client_returning(fake_stream)):
        with pytest.raises(LLMStreamStalledError) as exc_info:
            llm_svc.chat(system="sys", user="usr")

    # Partial char count surfaced for diagnostics.
    assert exc_info.value.idle_seconds > 60.0
    # The underlying stream must be closed even though we raised mid-iter
    # so we don't leak the HTTP socket.
    assert fake_stream.closed is True


def test_chat_does_not_raise_when_chunks_arrive_within_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Healthy stream (chunks within budget) returns the full text."""
    chunks = [
        _FakeChunk("Hello "),
        _FakeChunk("world"),
        _FakeChunk(None, finish_reason="stop"),
    ]
    fake_stream = _FakeStream(chunks)

    # Each call advances 5s — well under the 60s default.
    counter = {"t": 0.0}

    def fake_monotonic() -> float:
        counter["t"] += 5.0
        return counter["t"]

    monkeypatch.setattr(llm_svc.time, "monotonic", fake_monotonic)

    with patch.object(llm_svc, "_client", return_value=_fake_client_returning(fake_stream)):
        out = llm_svc.chat(system="sys", user="usr")
    assert out == "Hello world"
    # Stream is closed in the finally block on the success path too,
    # otherwise we'd leak the socket.
    assert fake_stream.closed is True


def test_chat_closes_stream_on_unexpected_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bug inside the iter loop must still release the socket."""

    class _BoomStream(_FakeStream):
        def __iter__(self):  # type: ignore[override]
            yield _FakeChunk("a")
            raise RuntimeError("simulated upstream crash")

    fake_stream = _BoomStream([])
    monkeypatch.setattr(llm_svc.time, "monotonic", lambda: 0.0)

    with patch.object(llm_svc, "_client", return_value=_fake_client_returning(fake_stream)):
        with pytest.raises(RuntimeError, match="simulated upstream crash"):
            llm_svc.chat(system="sys", user="usr")
    assert fake_stream.closed is True


# --- LLMStreamStalledError surface ---------------------------------------


def test_stalled_error_is_a_timeout_error() -> None:
    """Subclassing TimeoutError lets persona retry log "timeout" cleanly."""
    err = LLMStreamStalledError(idle_seconds=99.0, partial_chars=42)
    assert isinstance(err, TimeoutError)
    assert "99.0" in str(err)
    assert "42" in str(err)


# --- Real-time wall-clock sanity check -----------------------------------


def test_chat_calls_time_monotonic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Confirm the guard uses ``time.monotonic`` (not ``time.time``).

    ``time.time`` can jump backwards on NTP corrections and is
    unreliable for timeouts. Catches a refactor that swaps the two.
    """
    counter = {"n": 0, "t": 0.0}
    real_monotonic = time.monotonic  # capture before patching

    def fake_monotonic() -> float:
        counter["n"] += 1
        counter["t"] += 1.0
        # Touch the real clock so this test can't be silently bypassed
        # by a refactor that doesn't actually call monotonic().
        real_monotonic()
        return counter["t"]

    monkeypatch.setattr(llm_svc.time, "monotonic", fake_monotonic)

    chunks = [_FakeChunk("a"), _FakeChunk(None, finish_reason="stop")]
    fake_stream = _FakeStream(chunks)
    with patch.object(llm_svc, "_client", return_value=_fake_client_returning(fake_stream)):
        llm_svc.chat(system="sys", user="usr")

    # One baseline + at least one in-loop sample.
    assert counter["n"] >= 2
