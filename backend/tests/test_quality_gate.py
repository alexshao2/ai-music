"""Tests for the quality gate system: _extract_evaluation, prompt_validator,
audio_evaluator (heuristic), and quality gate endpoints."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import (
    Brief,
    QualityEvaluation,
    QualityScores,
    Section,
    SongDraft,
    SunoOutput,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_brief(**overrides: object) -> Brief:
    defaults = {"mood": "vui", "genre": "pop", "language": "vi"}
    defaults.update(overrides)
    return Brief(**defaults)  # type: ignore[arg-type]


def _make_draft(**overrides: object) -> SongDraft:
    defaults: dict[str, object] = {
        "id": "test-001",
        "title": "Test Song",
        "brief": _make_brief(),
        "key": "C major",
        "tempo_bpm": 120,
        "structure": [
            Section(section="intro", bars=4, chords=["C", "G"]),
            Section(section="verse", bars=8, chords=["Am", "F", "C", "G"]),
            Section(section="chorus", bars=8, chords=["F", "G", "Am", "C"]),
            Section(section="bridge", bars=4, chords=["Dm", "G"]),
        ],
        "lyrics": {"verse": "Dòng sông chảy qua\nMùa hè năm ấy", "chorus": "Và ta hát vang\nBài ca tuổi trẻ"},
        "compliance": {"bar_duration_math_ok": True, "chord_progression_concrete": True},
    }
    defaults.update(overrides)
    return SongDraft(**defaults)  # type: ignore[arg-type]


def _make_suno_output(**overrides: object) -> SunoOutput:
    defaults: dict[str, object] = {
        "title": "Test Song",
        "style": "upbeat pop, 120 bpm, C major, acoustic guitar, bright vocal, clap percussion",
        "lyrics": "[Verse]\nDòng sông chảy qua\nMùa hè năm ấy\nNắng vàng rực rỡ\nEm cười trong gió\n\n[Chorus]\nVà ta hát vang\nBài ca tuổi trẻ\nĐường phố rộn ràng\nTrái tim rực lửa",
    }
    defaults.update(overrides)
    return SunoOutput(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _extract_evaluation tests
# ---------------------------------------------------------------------------

class TestExtractEvaluation:
    def test_valid_critic_data(self) -> None:
        from app.services.council import _extract_evaluation

        critic = {
            "quality_scores": {
                "melody_catchiness": 8,
                "lyric_quality": 7,
                "harmonic_sophistication": 6,
                "structural_coherence": 7,
                "production_direction": 8,
                "genre_authenticity": 9,
                "overall": 7.6,
            },
            "verdict": "RELEASE",
            "compliance_summary": "Pass",
            "revision_brief": "",
        }
        result = _extract_evaluation(critic)
        assert result is not None
        assert result.verdict == "RELEASE"
        assert result.scores.melody_catchiness == 8.0
        assert result.scores.overall == 7.6

    def test_missing_quality_scores(self) -> None:
        from app.services.council import _extract_evaluation

        assert _extract_evaluation({}) is None
        assert _extract_evaluation({"quality_scores": None}) is None
        assert _extract_evaluation({"quality_scores": "bad"}) is None

    def test_invalid_verdict_inferred_from_score(self) -> None:
        from app.services.council import _extract_evaluation

        critic = {
            "quality_scores": {
                "melody_catchiness": 3,
                "lyric_quality": 3,
                "harmonic_sophistication": 3,
                "structural_coherence": 3,
                "production_direction": 3,
                "genre_authenticity": 3,
                "overall": 3.0,
            },
            "verdict": "INVALID_VALUE",
        }
        result = _extract_evaluation(critic)
        assert result is not None
        assert result.verdict == "REJECT"

    def test_score_clamping(self) -> None:
        from app.services.council import _extract_evaluation

        critic = {
            "quality_scores": {
                "melody_catchiness": 15,
                "lyric_quality": -5,
                "harmonic_sophistication": "not_a_number",
                "structural_coherence": 7,
                "production_direction": 7,
                "genre_authenticity": 7,
                "overall": 7.5,
            },
            "verdict": "RELEASE",
        }
        result = _extract_evaluation(critic)
        assert result is not None
        assert result.scores.melody_catchiness == 10.0
        assert result.scores.lyric_quality == 0.0
        assert result.scores.harmonic_sophistication == 0.0

    def test_verdict_boundary_revise(self) -> None:
        from app.services.council import _extract_evaluation

        critic = {
            "quality_scores": {"overall": 5.0, "melody_catchiness": 5},
            "verdict": "UNKNOWN",
        }
        result = _extract_evaluation(critic)
        assert result is not None
        assert result.verdict == "REVISE"


# ---------------------------------------------------------------------------
# prompt_validator tests
# ---------------------------------------------------------------------------

class TestPromptValidator:
    def test_valid_prompt(self) -> None:
        from app.services.prompt_validator import validate

        draft = _make_draft(suno_output=_make_suno_output())
        result = validate(draft)
        assert result.valid is True
        assert result.score > 0
        assert len(result.issues) == 0

    def test_no_suno_output(self) -> None:
        from app.services.prompt_validator import validate

        draft = _make_draft(suno_output=None)
        result = validate(draft)
        assert result.valid is False
        assert any("SunoOutput" in i for i in result.issues)

    def test_style_too_long(self) -> None:
        from app.services.prompt_validator import validate

        draft = _make_draft(suno_output=_make_suno_output(style="x" * 201))
        result = validate(draft)
        assert result.valid is False
        assert any("quá dài" in i for i in result.issues)

    def test_style_too_short(self) -> None:
        from app.services.prompt_validator import validate

        draft = _make_draft(suno_output=_make_suno_output(style="pop"))
        result = validate(draft)
        assert result.valid is False
        assert any("quá ngắn" in i for i in result.issues)

    def test_lyrics_no_section_tags(self) -> None:
        from app.services.prompt_validator import validate

        draft = _make_draft(
            suno_output=_make_suno_output(
                lyrics="line 1\nline 2\nline 3\nline 4\nline 5\nline 6\nline 7\nline 8\nline 9\nline 10"
            )
        )
        result = validate(draft)
        assert any("section tags" in i for i in result.issues)

    def test_lyrics_too_short(self) -> None:
        from app.services.prompt_validator import validate

        draft = _make_draft(
            suno_output=_make_suno_output(lyrics="[Verse]\nHello\nWorld")
        )
        result = validate(draft)
        assert any("quá ngắn" in i for i in result.issues)

    def test_compliance_failures_flagged(self) -> None:
        from app.services.prompt_validator import validate

        draft = _make_draft(
            suno_output=_make_suno_output(),
            compliance={"check_a": True, "check_b": False, "check_c": False},
        )
        result = validate(draft)
        assert any("Compliance" in i for i in result.issues)

    def test_no_compliance_gives_suggestion(self) -> None:
        from app.services.prompt_validator import validate

        draft = _make_draft(suno_output=_make_suno_output(), compliance={})
        result = validate(draft)
        assert any("compliance" in s.lower() for s in result.suggestions)

    def test_score_decreases_with_issues(self) -> None:
        from app.services.prompt_validator import validate

        good = validate(_make_draft(suno_output=_make_suno_output()))
        bad = validate(_make_draft(suno_output=None))
        assert good.score > bad.score

    def test_no_lyrics_at_all(self) -> None:
        from app.services.prompt_validator import validate

        draft = _make_draft(suno_output=_make_suno_output(lyrics=""), lyrics={})
        result = validate(draft)
        assert any("lyrics" in i.lower() for i in result.issues)


# ---------------------------------------------------------------------------
# audio_evaluator (heuristic) tests
# ---------------------------------------------------------------------------

class TestAudioEvaluatorHeuristic:
    def test_heuristic_with_full_draft(self) -> None:
        from app.services.audio_evaluator import _evaluate_heuristic

        draft = _make_draft(
            arrangement={"instruments": ["guitar", "piano"]},
            production={"suno_style_tags": ["pop"]},
        )
        result = _evaluate_heuristic(draft)
        assert result.verdict in ("RELEASE", "REVISE", "REJECT")
        assert 0 <= result.scores.overall <= 10
        assert result.feedback

    def test_heuristic_minimal_draft(self) -> None:
        from app.services.audio_evaluator import _evaluate_heuristic

        draft = _make_draft(
            lyrics={},
            arrangement={},
            production={},
            compliance={},
        )
        result = _evaluate_heuristic(draft)
        assert result.verdict == "REJECT"
        assert result.scores.overall < 5.0
        assert "Thiếu lyrics" in result.feedback

    def test_heuristic_low_compliance_caps_score(self) -> None:
        from app.services.audio_evaluator import _evaluate_heuristic

        draft = _make_draft(
            arrangement={"instruments": ["guitar"]},
            production={"suno_style_tags": ["pop"]},
            compliance={"a": True, "b": False, "c": False, "d": False, "e": False},
        )
        result = _evaluate_heuristic(draft)
        assert result.scores.overall <= 5.0

    def test_heuristic_verdict_matches_score(self) -> None:
        from app.services.audio_evaluator import _evaluate_heuristic

        draft = _make_draft(
            arrangement={"instruments": ["guitar"]},
            production={"suno_style_tags": ["pop"]},
        )
        result = _evaluate_heuristic(draft)
        if result.scores.overall >= 7.5:
            assert result.verdict == "RELEASE"
        elif result.scores.overall >= 5.0:
            assert result.verdict == "REVISE"
        else:
            assert result.verdict == "REJECT"

    def test_parse_evaluation_valid(self) -> None:
        from app.services.audio_evaluator import _parse_evaluation

        data = {
            "quality_scores": {
                "melody_catchiness": 8,
                "lyric_quality": 7,
                "harmonic_sophistication": 6,
                "structural_coherence": 7,
                "production_direction": 8,
                "genre_authenticity": 9,
                "overall": 7.6,
            },
            "verdict": "RELEASE",
            "feedback": "Great song.",
            "revision_notes": "",
        }
        result = _parse_evaluation(data)
        assert result.verdict == "RELEASE"
        assert result.scores.overall == 7.6

    def test_parse_evaluation_invalid_verdict(self) -> None:
        from app.services.audio_evaluator import _parse_evaluation

        data = {
            "quality_scores": {"overall": 3.0},
            "verdict": "GARBAGE",
        }
        result = _parse_evaluation(data)
        assert result.verdict == "REJECT"


# ---------------------------------------------------------------------------
# Quality gate endpoint tests
# ---------------------------------------------------------------------------

class TestQualityGateEndpoints:
    def test_compose_quality_endpoint(self) -> None:
        r = client.post(
            "/council/compose/quality",
            json=_make_brief().model_dump(),
        )
        assert r.status_code == 200
        draft = r.json()
        assert draft["id"]
        assert len(draft["council_log"]) == 6

    def test_compose_quality_custom_params(self) -> None:
        r = client.post(
            "/council/compose/quality?target_score=5.0&max_revisions=0",
            json=_make_brief().model_dump(),
        )
        assert r.status_code == 200

    def test_compose_quality_invalid_max_revisions(self) -> None:
        r = client.post(
            "/council/compose/quality?max_revisions=-1",
            json=_make_brief().model_dump(),
        )
        assert r.status_code == 422

    def test_compose_quality_invalid_target_score(self) -> None:
        r = client.post(
            "/council/compose/quality?target_score=15",
            json=_make_brief().model_dump(),
        )
        assert r.status_code == 422

    def test_evaluate_draft_endpoint(self) -> None:
        r1 = client.post(
            "/council/compose",
            json=_make_brief().model_dump(),
        )
        draft_id = r1.json()["id"]

        r2 = client.post(f"/studio/drafts/{draft_id}/evaluate")
        assert r2.status_code == 200
        evaluation = r2.json()
        assert evaluation["verdict"] in ("RELEASE", "REVISE", "REJECT")
        assert "scores" in evaluation
        assert 0 <= evaluation["scores"]["overall"] <= 10

    def test_get_quality_before_evaluate(self) -> None:
        r1 = client.post(
            "/council/compose",
            json=_make_brief().model_dump(),
        )
        draft_id = r1.json()["id"]
        r2 = client.get(f"/studio/drafts/{draft_id}/quality")
        assert r2.status_code == 404

    def test_get_quality_after_evaluate(self) -> None:
        r1 = client.post(
            "/council/compose",
            json=_make_brief().model_dump(),
        )
        draft_id = r1.json()["id"]
        client.post(f"/studio/drafts/{draft_id}/evaluate")
        r2 = client.get(f"/studio/drafts/{draft_id}/quality")
        assert r2.status_code == 200
        assert r2.json()["verdict"] in ("RELEASE", "REVISE", "REJECT")

    def test_validate_prompt_endpoint(self) -> None:
        r1 = client.post(
            "/council/compose",
            json=_make_brief().model_dump(),
        )
        draft_id = r1.json()["id"]
        r2 = client.post(f"/studio/drafts/{draft_id}/validate-prompt")
        assert r2.status_code == 200
        validation = r2.json()
        assert "valid" in validation
        assert "score" in validation
        assert "issues" in validation
        assert "suggestions" in validation

    def test_evaluate_nonexistent_draft(self) -> None:
        r = client.post("/studio/drafts/nonexistent-id/evaluate")
        assert r.status_code == 404

    def test_validate_nonexistent_draft(self) -> None:
        r = client.post("/studio/drafts/nonexistent-id/validate-prompt")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------

class TestSchemaValidation:
    def test_quality_scores_clamped_by_pydantic(self) -> None:
        import pytest

        with pytest.raises(Exception):
            QualityScores(melody_catchiness=11)
        with pytest.raises(Exception):
            QualityScores(lyric_quality=-1)

    def test_quality_scores_defaults(self) -> None:
        s = QualityScores()
        assert s.melody_catchiness == 0
        assert s.overall == 0

    def test_quality_evaluation_defaults(self) -> None:
        e = QualityEvaluation()
        assert e.verdict == "REVISE"
        assert e.attempt == 1
        assert e.max_attempts_reached is False

    def test_quality_evaluation_invalid_verdict(self) -> None:
        import pytest

        with pytest.raises(Exception):
            QualityEvaluation(verdict="INVALID")

    def test_song_draft_evaluation_optional(self) -> None:
        draft = _make_draft()
        assert draft.evaluation is None

    def test_song_draft_with_evaluation(self) -> None:
        evaluation = QualityEvaluation(
            scores=QualityScores(overall=8.0),
            verdict="RELEASE",
        )
        draft = _make_draft(evaluation=evaluation)
        assert draft.evaluation is not None
        assert draft.evaluation.verdict == "RELEASE"
