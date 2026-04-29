"""Tests for the streaming quality-gate council endpoint."""
from __future__ import annotations

import json as _j

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import Brief

client = TestClient(app)


def _drain(path: str, body: dict, params: dict | None = None) -> list[dict]:
    """POST to an SSE endpoint and parse all `data:` lines into dicts."""
    with client.stream("POST", path, json=body, params=params) as r:
        assert r.status_code == 200, r.text
        events: list[dict] = []
        for line in r.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            events.append(_j.loads(line[len("data: "):]))
    return events


def test_quality_stream_stub_one_attempt():
    """Without an LLM, the stub draft is deterministic and the gate should
    open on the first attempt (we don't reset / retry the stub)."""
    body = Brief(mood="hoài niệm", genre="ballad", language="vi").model_dump()
    events = _drain("/council/compose/quality/stream", body)

    types = [e["type"] for e in events]
    assert types[0] == "revision_started"
    assert events[0]["attempt"] == 1
    assert events[0]["max_attempts"] == 1  # stub never retries
    assert events[0]["target_score"] == 7.5

    # Inner persona events must be tagged with the attempt number.
    persona_events = [e for e in events if e["type"] in {"persona_started", "persona_completed"}]
    assert persona_events, "expected at least one persona event"
    for e in persona_events:
        assert e.get("attempt") == 1

    # revision_completed must come after the persona events and mark passed=True.
    rev_done = [e for e in events if e["type"] == "revision_completed"]
    assert len(rev_done) == 1
    assert rev_done[0]["passed"] is True
    assert rev_done[0]["attempt"] == 1

    # Final draft + done.
    drafts = [e for e in events if e["type"] == "draft"]
    assert len(drafts) == 1
    assert drafts[0]["best_attempt"] == 1
    assert drafts[0]["draft"]["id"]
    assert types[-1] == "done"


def _stub_audio_evaluator_to_match_critic(monkeypatch) -> None:
    """Force the independent A&R evaluator to mirror the Critic's score.

    Tests that pre-date the independent evaluator wiring assumed the gate
    score *was* the Critic score. Since the gate now averages Critic with
    the audio evaluator, those tests stay valid by pinning the audio
    evaluator to whatever the Critic stamped onto the draft.
    """
    from app.schemas import QualityEvaluation, QualityScores, SongDraft
    from app.services import audio_evaluator

    def _mirror(draft: SongDraft) -> QualityEvaluation:
        if draft.evaluation is not None:
            critic_score = draft.evaluation.scores.overall
        else:
            critic_score = 0.0
        return QualityEvaluation(
            scores=QualityScores(
                melody_catchiness=critic_score,
                lyric_quality=critic_score,
                harmonic_sophistication=critic_score,
                structural_coherence=critic_score,
                production_direction=critic_score,
                genre_authenticity=critic_score,
                overall=critic_score,
            ),
            verdict="RELEASE" if critic_score >= 7.5 else "REVISE",
            feedback="mirrored",
            revision_notes="",
        )

    monkeypatch.setattr(audio_evaluator, "evaluate_draft", _mirror)


def test_quality_stream_loops_until_passed(monkeypatch):
    """When the inner draft starts low and improves, the loop must stop on
    the first attempt that meets ``target_score`` and yield that draft."""
    from app.schemas import (
        QualityEvaluation,
        QualityScores,
        Section,
        SongDraft,
    )
    from app.services import council as council_svc

    base_brief = Brief(mood="hoài niệm", genre="ballad", language="vi")

    scores_seq = [4.0, 8.5, 9.5]  # attempt 1 fails, attempt 2 passes target=7.5
    has_llm_calls = {"n": 0}

    def fake_inner(brief, *, refine):
        idx = has_llm_calls["n"]
        has_llm_calls["n"] += 1
        score = scores_seq[idx]
        evaluation = QualityEvaluation(
            scores=QualityScores(
                melody_catchiness=score,
                lyric_quality=score,
                harmonic_sophistication=score,
                structural_coherence=score,
                production_direction=score,
                genre_authenticity=score,
                overall=score,
            ),
            verdict="RELEASE" if score >= 7.5 else "REVISE",
            feedback="auto",
            revision_notes="Lyricist needs sharper imagery in chorus",
        )
        draft = SongDraft(
            id=f"fake-{idx}",
            title=f"attempt {idx + 1}",
            brief=brief,
            key="C major",
            tempo_bpm=100,
            structure=[Section(section="verse", bars=8, chords=["C"])],
            lyrics={"verse_1": "lyric text"},
            arrangement={},
            production={},
            council_log=[],
            evaluation=evaluation,
        )
        # Mimic the order of compose_stream events.
        yield {"type": "persona_started", "role": "theorist", "name": "T", "index": 0, "total": 1}
        yield {"type": "persona_completed", "role": "theorist", "name": "T", "message": "ok", "contributions": {}}
        yield {"type": "draft", "draft": draft}
        yield {"type": "done"}

    # Force the LLM-mode branch (`has_llm` is a Pydantic property — set the
    # underlying creds instead) and stub the inner generator + evaluator.
    monkeypatch.setattr(council_svc.settings, "llm_api_key", "test")
    monkeypatch.setattr(council_svc.settings, "llm_base_url", "https://x.test/v1")
    monkeypatch.setattr(council_svc, "_compose_stream_llm", fake_inner)
    _stub_audio_evaluator_to_match_critic(monkeypatch)
    assert council_svc.settings.has_llm

    events = list(
        council_svc.compose_quality_stream(
            base_brief, target_score=7.5, max_revisions=2, refine=True
        )
    )

    rev_started = [e for e in events if e["type"] == "revision_started"]
    rev_done = [e for e in events if e["type"] == "revision_completed"]
    drafts = [e for e in events if e["type"] == "draft"]

    # 2 attempts: first fails (score 4.0), second passes (8.5). Third never runs.
    assert [e["attempt"] for e in rev_started] == [1, 2]
    assert [round(e["score"], 1) for e in rev_done] == [4.0, 8.5]
    assert [e["passed"] for e in rev_done] == [False, True]

    # Best draft is from attempt 2.
    assert len(drafts) == 1
    assert drafts[0]["best_attempt"] == 2
    assert drafts[0]["draft"].id == "fake-1"

    # Attempt 1 starts with the original (empty) brief.notes...
    assert events[0]["brief_notes"] == ""
    # ...but attempt 2's revision_started must carry the previous attempt's
    # revision_brief appended into brief.notes — that's how the council
    # actually changes its behaviour on retry rather than re-rolling identical
    # outputs.
    attempt2 = next(e for e in events if e["type"] == "revision_started" and e["attempt"] == 2)
    assert "HỘI ĐỒNG REVISION #1" in attempt2["brief_notes"]
    assert "Lyricist needs sharper imagery" in attempt2["brief_notes"]


def test_quality_stream_keeps_best_when_target_unreached(monkeypatch):
    """If no attempt meets target, the highest-scoring draft must be returned
    and ``max_attempts_reached`` must be flagged on its evaluation."""
    from app.schemas import (
        QualityEvaluation,
        QualityScores,
        Section,
        SongDraft,
    )
    from app.services import council as council_svc

    base_brief = Brief(mood="hoài niệm", genre="ballad", language="vi")

    # Attempt 2 is the best, but still under 9.0 target.
    scores_seq = [3.0, 6.0, 5.0]
    n = {"i": 0}

    def fake_inner(brief, *, refine):
        idx = n["i"]
        n["i"] += 1
        score = scores_seq[idx]
        draft = SongDraft(
            id=f"draft-{idx}",
            title="t", brief=brief, key="C", tempo_bpm=100,
            structure=[Section(section="verse", bars=8, chords=["C"])],
            lyrics={}, arrangement={}, production={}, council_log=[],
            evaluation=QualityEvaluation(
                scores=QualityScores(
                    melody_catchiness=score, lyric_quality=score,
                    harmonic_sophistication=score, structural_coherence=score,
                    production_direction=score, genre_authenticity=score,
                    overall=score,
                ),
                verdict="REVISE", feedback="", revision_notes="more punch",
            ),
        )
        yield {"type": "persona_completed", "role": "critic", "name": "Critic", "message": "ok", "contributions": {}}
        yield {"type": "draft", "draft": draft}
        yield {"type": "done"}

    monkeypatch.setattr(council_svc.settings, "llm_api_key", "test")
    monkeypatch.setattr(council_svc.settings, "llm_base_url", "https://x.test/v1")
    monkeypatch.setattr(council_svc, "_compose_stream_llm", fake_inner)
    _stub_audio_evaluator_to_match_critic(monkeypatch)
    assert council_svc.settings.has_llm

    events = list(
        council_svc.compose_quality_stream(
            base_brief, target_score=9.0, max_revisions=2, refine=True
        )
    )

    drafts = [e for e in events if e["type"] == "draft"]
    assert len(drafts) == 1
    # Best score was 6.0 on attempt 2.
    assert drafts[0]["best_attempt"] == 2
    chosen = drafts[0]["draft"]
    assert chosen.evaluation is not None
    assert chosen.evaluation.scores.overall == 6.0
    assert chosen.evaluation.max_attempts_reached is True


def test_quality_stream_independent_evaluator_blocks_inflated_critic(monkeypatch):
    """Critic over-rates a draft (9.0); independent A&R sees the same draft
    as 4.0. Gate score must be the average (6.5) — below target — so the
    council must retry instead of releasing on attempt 1."""
    from app.schemas import (
        QualityEvaluation,
        QualityScores,
        Section,
        SongDraft,
    )
    from app.services import audio_evaluator
    from app.services import council as council_svc

    base_brief = Brief(mood="hoài niệm", genre="ballad", language="vi")

    # Critic is wildly optimistic across all attempts.
    critic_scores = [9.0, 9.0, 9.0]
    # Independent evaluator catches reality — only attempt 3 is actually good.
    indep_scores = [4.0, 5.0, 8.0]
    n = {"i": 0}

    def fake_inner(brief, *, refine):
        idx = n["i"]
        n["i"] += 1
        score = critic_scores[idx]
        evaluation = QualityEvaluation(
            scores=QualityScores(
                melody_catchiness=score, lyric_quality=score,
                harmonic_sophistication=score, structural_coherence=score,
                production_direction=score, genre_authenticity=score,
                overall=score,
            ),
            verdict="RELEASE",
            feedback="Critic loves it",
            revision_notes="",
        )
        draft = SongDraft(
            id=f"d{idx}",
            title="t", brief=brief, key="C", tempo_bpm=100,
            structure=[Section(section="verse", bars=8, chords=["C"])],
            lyrics={"verse_1": "x"},
            arrangement={}, production={}, council_log=[],
            evaluation=evaluation,
        )
        yield {"type": "draft", "draft": draft}
        yield {"type": "done"}

    def fake_independent(draft):
        # Independent score is keyed on draft id so we can pin a sequence.
        idx = int(draft.id[1:])
        s = indep_scores[idx]
        return QualityEvaluation(
            scores=QualityScores(
                melody_catchiness=s, lyric_quality=s,
                harmonic_sophistication=s, structural_coherence=s,
                production_direction=s, genre_authenticity=s, overall=s,
            ),
            verdict="REVISE",
            feedback="A&R unimpressed",
            revision_notes="Hook too weak; lyric clichéd",
        )

    monkeypatch.setattr(council_svc.settings, "llm_api_key", "test")
    monkeypatch.setattr(council_svc.settings, "llm_base_url", "https://x.test/v1")
    monkeypatch.setattr(council_svc, "_compose_stream_llm", fake_inner)
    monkeypatch.setattr(audio_evaluator, "evaluate_draft", fake_independent)

    events = list(
        council_svc.compose_quality_stream(
            base_brief, target_score=7.5, max_revisions=2, refine=True
        )
    )

    rev_done = [e for e in events if e["type"] == "revision_completed"]
    # Gate score = (critic + indep) / 2 = (9.0 + 4.0)/2 = 6.5,
    # then (9.0 + 5.0)/2 = 7.0, then (9.0 + 8.0)/2 = 8.5.
    gate_scores = [round(e["score"], 2) for e in rev_done]
    assert gate_scores == [6.5, 7.0, 8.5]
    # Each event must surface both component scores.
    for e in rev_done:
        assert "critic_score" in e
        assert "independent_score" in e
    assert [e["passed"] for e in rev_done] == [False, False, True]
    # Critic-only would have been [True, True, True] from attempt 1 — gate
    # logic correctly forces 2 retries before release.

    drafts = [e for e in events if e["type"] == "draft"]
    chosen = drafts[0]["draft"]
    # The chosen draft carries BOTH evaluations.
    assert chosen.evaluation is not None
    assert chosen.independent_evaluation is not None
    assert chosen.evaluation.scores.overall == 9.0
    assert chosen.independent_evaluation.scores.overall == 8.0


def test_quality_stream_independent_evaluator_failure_falls_back_to_critic(monkeypatch):
    """If the independent evaluator raises, the gate must still work using
    Critic alone (no hard dependency on the second LLM pass)."""
    from app.schemas import (
        QualityEvaluation,
        QualityScores,
        Section,
        SongDraft,
    )
    from app.services import audio_evaluator
    from app.services import council as council_svc

    base_brief = Brief(mood="x", genre="y", language="vi")

    def fake_inner(brief, *, refine):
        evaluation = QualityEvaluation(
            scores=QualityScores(overall=8.0),
            verdict="RELEASE", feedback="ok", revision_notes="",
        )
        draft = SongDraft(
            id="d0", title="t", brief=brief, key="C", tempo_bpm=100,
            structure=[Section(section="verse", bars=8, chords=["C"])],
            lyrics={"verse_1": "x"},
            arrangement={}, production={}, council_log=[],
            evaluation=evaluation,
        )
        yield {"type": "draft", "draft": draft}
        yield {"type": "done"}

    def boom(_draft):
        raise RuntimeError("LLM down")

    monkeypatch.setattr(council_svc.settings, "llm_api_key", "test")
    monkeypatch.setattr(council_svc.settings, "llm_base_url", "https://x.test/v1")
    monkeypatch.setattr(council_svc, "_compose_stream_llm", fake_inner)
    monkeypatch.setattr(audio_evaluator, "evaluate_draft", boom)

    events = list(
        council_svc.compose_quality_stream(
            base_brief, target_score=7.5, max_revisions=2, refine=True
        )
    )

    rev_done = [e for e in events if e["type"] == "revision_completed"]
    assert len(rev_done) == 1
    assert round(rev_done[0]["score"], 1) == 8.0  # critic-only fallback
    assert rev_done[0]["critic_score"] == 8.0
    assert rev_done[0]["independent_score"] == 0.0
    assert rev_done[0]["passed"] is True

    drafts = [e for e in events if e["type"] == "draft"]
    assert drafts[0]["draft"].independent_evaluation is None


def test_quality_stream_endpoint_emits_keepalive(monkeypatch):
    """The new endpoint must reuse the same SSE keepalive plumbing as the
    plain compose stream — Cloudflare Tunnel will drop a 100s-idle response."""
    import time

    from app.routers import council as router_mod
    from app.services import council as council_svc

    def slow_quality(_brief, *, target_score, max_revisions, refine):
        yield {"type": "revision_started", "attempt": 1, "max_attempts": 1,
               "target_score": target_score, "brief_notes": ""}
        time.sleep(0.3)
        yield {"type": "revision_completed", "attempt": 1, "score": 9.0,
               "verdict": "RELEASE", "passed": True, "revision_brief": ""}
        yield {"type": "done"}

    monkeypatch.setattr(council_svc, "compose_quality_stream", slow_quality)
    monkeypatch.setattr(router_mod, "SSE_KEEPALIVE_SECONDS", 0.08)

    body = Brief(mood="x", genre="y", language="vi").model_dump()
    with client.stream("POST", "/council/compose/quality/stream", json=body) as r:
        assert r.status_code == 200
        raw = b"".join(r.iter_bytes()).decode("utf-8", errors="replace")

    assert ": keepalive" in raw
    assert '"type": "revision_started"' in raw
    assert '"type": "revision_completed"' in raw
