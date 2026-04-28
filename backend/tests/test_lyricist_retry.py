"""Integration test: _run_persona_with_retry retries the Lyricist on bad output.

We monkey-patch ``_run_persona`` to return a placeholder-laden dict on the
first call and a clean dict on the second, and assert the retry pipeline
observes the validator, forwards the nudge, and returns the clean result.
"""
from __future__ import annotations

from typing import Any

import pytest

from app.schemas import Brief
from app.services import council as council_svc

_BAD = {
    "message": "draft 1",
    "contributions": {
        "title": "X",
        "hook_line": "Em đi",
        "lyrics": {
            "verse_1": "[chờ Lyricist điền]",
            "pre_chorus": "",
            "chorus": "<full lyric block>",
            "bridge": "placeholder placeholder",
        },
    },
}

_GOOD = {
    "message": "draft 2",
    "contributions": {
        "title": "Tháng Tư",
        "hook_line": "Tháng tư về trên Hai Bà Trưng",
        "lyrics": {
            "verse_1": (
                "Tháng tư nắng vương trên Lê Văn Sỹ\n"
                "Em đi rồi, tách trà nguội ngắt"
            ),
            "pre_chorus": (
                "Gió vẫn thổi qua căn phòng nhỏ\n"
                "Những ký ức cũ vẫn còn đây"
            ),
            "chorus": (
                "Tháng tư về trên Hai Bà Trưng\n"
                "Em đi rồi nắng vẫn còn vương"
            ),
            "bridge": (
                "Và tôi vẫn đi qua con phố cũ\n"
                "Nhớ ngày em còn ngồi bên tôi"
            ),
        },
    },
}


@pytest.fixture
def brief() -> Brief:
    return Brief(
        mood="hoài niệm",
        genre="V-pop Ballad",
        language="vi",
        duration_sec=210,
        references=[],
        notes=None,
    )


def _find_lyricist():
    for p in council_svc.COUNCIL_PERSONAS:
        if p.role == "lyricist":
            return p
    raise AssertionError("Lyricist persona missing from COUNCIL_PERSONAS")


def test_lyricist_retries_on_placeholder_and_returns_clean(
    monkeypatch: pytest.MonkeyPatch, brief: Brief
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_run_persona(
        persona, b, prior_turns, prior_contributions, *, retry_nudge: str = ""
    ):
        calls.append({"retry_nudge": retry_nudge})
        if len(calls) == 1:
            return _BAD
        return _GOOD

    monkeypatch.setattr(council_svc, "_run_persona", fake_run_persona)

    lyricist = _find_lyricist()
    result = council_svc._run_persona_with_retry(lyricist, brief, [], {})

    assert result == _GOOD
    assert len(calls) == 2, "validator should have triggered exactly one retry"
    # The retry prompt must contain the placeholder fix nudge.
    assert calls[0]["retry_nudge"] == "", "first attempt must not carry a nudge"
    assert "LẦN TRƯỚC" in calls[1]["retry_nudge"]


def test_lyricist_returns_none_when_all_retries_stay_bad(
    monkeypatch: pytest.MonkeyPatch, brief: Brief
) -> None:
    def fake_run_persona(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return _BAD

    monkeypatch.setattr(council_svc, "_run_persona", fake_run_persona)

    lyricist = _find_lyricist()
    result = council_svc._run_persona_with_retry(lyricist, brief, [], {})
    assert result is None


def test_non_lyricist_persona_skips_validator(
    monkeypatch: pytest.MonkeyPatch, brief: Brief
) -> None:
    """Composer (or any non-lyricist) shouldn't go through the lyric validator.

    Even if its JSON happens to contain the word 'placeholder', we accept
    the first successful call.
    """

    def fake_run_persona(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "message": "ok",
            "contributions": {"hook_idea": "placeholder hook"},
        }

    monkeypatch.setattr(council_svc, "_run_persona", fake_run_persona)

    composer = next(p for p in council_svc.COUNCIL_PERSONAS if p.role == "composer")
    result = council_svc._run_persona_with_retry(composer, brief, [], {})
    assert result is not None
    assert result["contributions"]["hook_idea"] == "placeholder hook"
