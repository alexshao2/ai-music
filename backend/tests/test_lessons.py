"""Tests for the cross-session lessons store."""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from app.services import lessons as lessons_mod
from app.services.lessons import (
    Lesson,
    brief_signature,
    collect_lessons_from_run,
    format_lessons_for_prompt,
    recent_lessons_for,
    record_lessons,
)


@pytest.fixture
def tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    """Point the lessons store at an isolated SQLite file for the test."""
    db = tmp_path / "lessons.sqlite"
    monkeypatch.setenv("COUNCIL_LESSONS_DB", str(db))
    monkeypatch.delenv("COUNCIL_LESSONS_DISABLED", raising=False)
    yield db


# --- Brief signature ------------------------------------------------------


def test_brief_signature_normalises_whitespace_and_case() -> None:
    a = brief_signature(language="vi", genre="V-pop ballad", mood="Hoài niệm")
    b = brief_signature(
        language="VI", genre="  v-pop   ballad ", mood="hoài  niệm",
    )
    assert a == b


def test_brief_signature_distinct_for_different_inputs() -> None:
    a = brief_signature(language="vi", genre="ballad", mood="hoài niệm")
    b = brief_signature(language="vi", genre="ballad", mood="vui tươi")
    c = brief_signature(language="en", genre="ballad", mood="hoài niệm")
    assert a != b
    assert a != c


def test_brief_signature_handles_none_fields() -> None:
    sig = brief_signature(language=None, genre=None, mood=None)
    assert sig == "||"


# --- Recording + reading round-trip --------------------------------------


def _row(role: str = "lyricist", code: str = "cliche_detected") -> dict:
    return {
        "persona_role": role,
        "issue_kind": "lyric",
        "issue_code": code,
        "issue_message": "Câu chứa cliché 'em là duy nhất'",
    }


def test_record_then_read_returns_recent(tmp_db: Path) -> None:
    sig = brief_signature(language="vi", genre="ballad", mood="hoài niệm")
    inserted = record_lessons(sig, [_row(), _row(code="placeholder")])
    assert inserted == 2

    out = recent_lessons_for(sig, "lyricist")
    assert [le.issue_code for le in out] == ["placeholder", "cliche_detected"]
    assert all(isinstance(le, Lesson) for le in out)


def test_recent_lessons_filters_by_role(tmp_db: Path) -> None:
    sig = brief_signature(language="vi", genre="ballad", mood="hoài niệm")
    record_lessons(
        sig,
        [
            _row(role="lyricist", code="cliche_detected"),
            _row(role="producer", code="suno_style_too_long"),
        ],
    )
    lyr = recent_lessons_for(sig, "lyricist")
    prd = recent_lessons_for(sig, "producer")
    assert [le.issue_code for le in lyr] == ["cliche_detected"]
    assert [le.issue_code for le in prd] == ["suno_style_too_long"]


def test_recent_lessons_filters_by_signature(tmp_db: Path) -> None:
    a = brief_signature(language="vi", genre="ballad", mood="hoài niệm")
    b = brief_signature(language="en", genre="ballad", mood="upbeat")
    record_lessons(a, [_row(code="a_only")])
    record_lessons(b, [_row(code="b_only")])
    assert [le.issue_code for le in recent_lessons_for(a, "lyricist")] == [
        "a_only"
    ]
    assert [le.issue_code for le in recent_lessons_for(b, "lyricist")] == [
        "b_only"
    ]


def test_record_lessons_skips_malformed_rows(tmp_db: Path) -> None:
    sig = brief_signature(language="vi", genre="ballad", mood="hoài niệm")
    inserted = record_lessons(
        sig,
        [
            _row(),  # valid
            {"persona_role": "", "issue_kind": "lyric", "issue_code": "x", "issue_message": "y"},  # empty role
            {"persona_role": "lyricist", "issue_kind": "lyric", "issue_code": "x", "issue_message": ""},  # empty msg
            "not a mapping",  # type: ignore[list-item]
        ],
    )
    assert inserted == 1
    assert len(recent_lessons_for(sig, "lyricist")) == 1


def test_recent_lessons_for_missing_db_returns_empty(
    tmp_db: Path,
) -> None:
    # tmp_db env var points at a path, but we never created it.
    sig = brief_signature(language="vi", genre="ballad", mood="hoài niệm")
    assert recent_lessons_for(sig, "lyricist") == []


def test_recent_lessons_for_unknown_signature_returns_empty(
    tmp_db: Path,
) -> None:
    sig = brief_signature(language="vi", genre="ballad", mood="hoài niệm")
    record_lessons(sig, [_row()])

    other = brief_signature(language="vi", genre="rock", mood="hoài niệm")
    assert recent_lessons_for(other, "lyricist") == []


def test_recent_lessons_limit_caps_results(tmp_db: Path) -> None:
    sig = brief_signature(language="vi", genre="ballad", mood="hoài niệm")
    record_lessons(sig, [_row(code=f"code_{i}") for i in range(5)])

    out = recent_lessons_for(sig, "lyricist", limit=2)
    assert len(out) == 2
    # Most recent first; insertion preserves rowid order so the last
    # two codes win.
    codes = [le.issue_code for le in out]
    assert codes == ["code_4", "code_3"]


# --- Disabled mode --------------------------------------------------------


def test_disabled_flag_makes_record_a_noop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setenv("COUNCIL_LESSONS_DB", str(tmp_path / "x.sqlite"))
    monkeypatch.setenv("COUNCIL_LESSONS_DISABLED", "1")
    sig = brief_signature(language="vi", genre="ballad", mood="hoài niệm")
    assert record_lessons(sig, [_row()]) == 0
    assert recent_lessons_for(sig, "lyricist") == []


def test_empty_signature_skips_writes(tmp_db: Path) -> None:
    assert record_lessons("", [_row()]) == 0


# --- Per-bucket cap -------------------------------------------------------


def test_per_bucket_cap_trims_oldest_rows(
    tmp_db: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inserting more than _PER_BUCKET_CAP into one bucket trims down."""
    monkeypatch.setattr(lessons_mod, "_PER_BUCKET_CAP", 5)
    sig = brief_signature(language="vi", genre="ballad", mood="hoài niệm")
    record_lessons(sig, [_row(code=f"code_{i}") for i in range(8)])

    out = recent_lessons_for(sig, "lyricist", limit=99)
    assert len(out) == 5
    codes = {le.issue_code for le in out}
    # Keep newest 5 of 8 → code_3 .. code_7
    assert codes == {"code_3", "code_4", "code_5", "code_6", "code_7"}


# --- Prompt formatting ----------------------------------------------------


def test_format_lessons_for_prompt_renders_block() -> None:
    block = format_lessons_for_prompt(
        [
            Lesson(
                persona_role="lyricist",
                issue_kind="lyric",
                issue_code="cliche_detected",
                issue_message="Câu chứa 'em là duy nhất'",
                created_at=0.0,
            ),
        ]
    )
    assert "BRIEF NÀY TRƯỚC ĐÂY HAY MẮC" in block
    assert "lyric/cliche_detected" in block
    assert "em là duy nhất" in block
    # Must end with an instructional line so the model knows what to do.
    assert "đừng" in block.lower() or "tránh" in block.lower()


def test_format_lessons_for_prompt_empty_returns_empty_string() -> None:
    assert format_lessons_for_prompt([]) == ""


# --- collect_lessons_from_run ---------------------------------------------


def test_collect_from_compliance_issues() -> None:
    class Issue:
        def __init__(self, role: str, code: str, msg: str) -> None:
            self.persona_role = role
            self.code = code
            self.message = msg

    rows = collect_lessons_from_run(
        compliance_issues=[
            Issue("producer", "suno_style_too_long", "Style 250 chars > 200"),
            Issue("theorist", "chord_not_in_scale", "F# not in C major"),
        ],
    )
    codes = {(r["persona_role"], r["issue_code"]) for r in rows}
    assert codes == {
        ("producer", "suno_style_too_long"),
        ("theorist", "chord_not_in_scale"),
    }
    assert all(r["issue_kind"] == "compliance" for r in rows)


def test_collect_from_quality_concerns() -> None:
    rows = collect_lessons_from_run(
        quality_concerns_by_role={
            "arranger": [("structural_coherence", 4.0)],
            "theorist": [("genre_authenticity", 5.5)],
        },
    )
    codes = {(r["persona_role"], r["issue_code"]) for r in rows}
    assert ("arranger", "structural_coherence") in codes
    assert ("theorist", "genre_authenticity") in codes
    assert all(r["issue_kind"] == "quality" for r in rows)


def test_collect_from_lyric_issues_uses_lyricist_role() -> None:
    class LIssue:
        def __init__(self, code: str, msg: str) -> None:
            self.code = code
            self.message = msg

    rows = collect_lessons_from_run(
        lyric_issues=[LIssue("cliche_detected", "câu chứa 'em là duy nhất'")],
    )
    assert rows == [
        {
            "persona_role": "lyricist",
            "issue_kind": "lyric",
            "issue_code": "cliche_detected",
            "issue_message": "câu chứa 'em là duy nhất'",
        }
    ]


def test_collect_with_no_inputs_returns_empty() -> None:
    assert collect_lessons_from_run() == []


# --- Round-trip via collect + record --------------------------------------


def test_full_round_trip_records_and_surfaces_for_persona(
    tmp_db: Path,
) -> None:
    """End-to-end: collect issues from a run → record → read for persona
    → format → string includes the original message."""

    class Issue:
        def __init__(self, role: str, code: str, msg: str) -> None:
            self.persona_role = role
            self.code = code
            self.message = msg

    sig = brief_signature(language="vi", genre="ballad", mood="hoài niệm")
    rows = collect_lessons_from_run(
        compliance_issues=[
            Issue("producer", "suno_style_too_long", "Style 250 chars"),
        ],
    )
    record_lessons(sig, rows)

    lessons = recent_lessons_for(sig, "producer")
    block = format_lessons_for_prompt(lessons)
    assert "suno_style_too_long" in block
    assert "Style 250 chars" in block
