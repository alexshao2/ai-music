"""LLM-based A&R quality evaluator for SongDrafts.

Evaluates a finished SongDraft as a world-class A&R executive would,
scoring across multiple quality dimensions and returning an actionable
verdict (RELEASE / REVISE / REJECT).

When audio analysis becomes available (Phase 3), this module will also
accept an audio URL and run algorithmic checks (tempo, key, LUFS).
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.config import settings
from app.schemas import QualityEvaluation, QualityScores, SongDraft
from app.services import knowledge as knowledge_svc
from app.services import llm as llm_svc

log = logging.getLogger(__name__)

_EVALUATOR_SYSTEM = (
    "BẠN LÀ: A&R executive cấp thế giới (Rick Rubin + Jimmy Iovine + Quincy Jones). "
    "Nhiệm vụ: đánh giá SongDraft NGHIÊM KHẮC, TRUNG THỰC, KHÔNG NỊNH.\n\n"
    "CHẤM ĐIỂM 1-10 cho 6 tiêu chí:\n"
    "1. melody_catchiness: hook có catchy, singalong, memorable? peak note placement đúng? "
    "hook recipe rõ ràng và hiệu quả?\n"
    "2. lyric_quality: imagery CỤ THỂ (không generic)? cliché-free? emotional depth? "
    "rhyme scheme tự nhiên? prosody tốt (stress đúng nhịp)?\n"
    "3. harmonic_sophistication: chord variety (không lặp 4 chord toàn bài)? "
    "modal interchange? bridge có tonal surprise? secondary dominants?\n"
    "4. structural_coherence: dynamic arc rõ ràng (có climax)? strip-down section? "
    "section contrast (verse ≠ chorus)? final chorus distinct?\n"
    "5. production_direction: Suno style tags match genre? FX values CỤ THỂ? "
    "references phù hợp language/genre? LUFS target hợp lý?\n"
    "6. genre_authenticity: đặc trưng genre cookbook match (instruments, time signature, "
    "articulation, vocal style)? Không trộn genre sai?\n\n"
    "overall = weighted avg: melody 20% + lyric 20% + genre 20% + structure 15% + "
    "production 15% + harmony 10%\n\n"
    "VERDICT:\n"
    "- RELEASE: overall >= 7.5 — bài đạt chuẩn xuất bản, đẳng cấp\n"
    "- REVISE: 5.0 <= overall < 7.5 — có tiềm năng nhưng cần sửa cụ thể\n"
    "- REJECT: overall < 5.0 — chất lượng thấp, cần viết lại\n\n"
    "OUTPUT FORMAT (JSON duy nhất, không commentary):\n"
    '{"quality_scores": {"melody_catchiness": <int>, "lyric_quality": <int>, '
    '"harmonic_sophistication": <int>, "structural_coherence": <int>, '
    '"production_direction": <int>, "genre_authenticity": <int>, '
    '"overall": <float>}, '
    '"verdict": "<RELEASE|REVISE|REJECT>", '
    '"feedback": "<2-3 paragraphs đánh giá chi tiết, cite section cụ thể>", '
    '"revision_notes": "<nếu REVISE/REJECT: 1 paragraph hướng dẫn sửa CỤ THỂ>"}'
)


def evaluate_draft(draft: SongDraft) -> QualityEvaluation:
    """Run an LLM-based A&R review of a SongDraft.

    Falls back to a heuristic evaluation when no LLM is configured.
    """
    if settings.has_llm:
        try:
            return _evaluate_with_llm(draft)
        except Exception:
            log.exception("LLM A&R evaluation failed; falling back to heuristic")
    return _evaluate_heuristic(draft)


def _evaluate_with_llm(draft: SongDraft) -> QualityEvaluation:
    genre_chunks = knowledge_svc.search(draft.brief.genre, k=2)
    genre_context = "\n\n".join(
        f"### {c.title}\n{c.excerpt}" for c in genre_chunks
    ) if genre_chunks else "(no genre knowledge)"

    lyrics_text = "\n\n".join(
        f"[{k}]\n{v}" for k, v in (draft.lyrics_with_markers or draft.lyrics).items()
    )
    arrangement_text = json.dumps(draft.arrangement, ensure_ascii=False, indent=2)
    production_text = json.dumps(draft.production, ensure_ascii=False, indent=2)
    suno_style = draft.suno_output.style if draft.suno_output else "(none)"

    user_prompt = f"""## SongDraft to evaluate
- Title: {draft.title}
- Genre: {draft.brief.genre}
- Mood: {draft.brief.mood}
- Language: {draft.brief.language}
- Key: {draft.key}
- Tempo: {draft.tempo_bpm} BPM
- Duration target: {draft.brief.duration_sec}s
- Structure: {", ".join(s.section for s in draft.structure)}

## Lyrics
{lyrics_text or "(no lyrics)"}

## Arrangement
{arrangement_text}

## Production
{production_text}

## Suno Style String
{suno_style}

## Genre Knowledge (from cookbook)
{genre_context}

## Compliance checks
{json.dumps(draft.compliance, ensure_ascii=False) if draft.compliance else "(none)"}

Evaluate this draft. Reply with a SINGLE JSON object."""

    result = llm_svc.chat_json(system=_EVALUATOR_SYSTEM, user=user_prompt)
    return _parse_evaluation(result)


def _parse_evaluation(data: dict[str, Any]) -> QualityEvaluation:
    raw_scores = data.get("quality_scores", {})

    def _clamp(v: Any) -> float:
        try:
            return max(0.0, min(10.0, float(v)))
        except (TypeError, ValueError):
            return 0.0

    scores = QualityScores(
        melody_catchiness=_clamp(raw_scores.get("melody_catchiness")),
        lyric_quality=_clamp(raw_scores.get("lyric_quality")),
        harmonic_sophistication=_clamp(raw_scores.get("harmonic_sophistication")),
        structural_coherence=_clamp(raw_scores.get("structural_coherence")),
        production_direction=_clamp(raw_scores.get("production_direction")),
        genre_authenticity=_clamp(raw_scores.get("genre_authenticity")),
        overall=_clamp(raw_scores.get("overall")),
    )

    verdict_raw = str(data.get("verdict", "REVISE")).upper()
    if verdict_raw not in ("RELEASE", "REVISE", "REJECT"):
        if scores.overall >= 7.5:
            verdict_raw = "RELEASE"
        elif scores.overall >= 5.0:
            verdict_raw = "REVISE"
        else:
            verdict_raw = "REJECT"

    return QualityEvaluation(
        scores=scores,
        verdict=verdict_raw,  # type: ignore[arg-type]
        feedback=str(data.get("feedback", "")),
        revision_notes=str(data.get("revision_notes", "")),
    )


def _evaluate_heuristic(draft: SongDraft) -> QualityEvaluation:
    """Score based on structural heuristics when no LLM is available."""
    s = QualityScores()
    notes: list[str] = []

    has_lyrics = bool(draft.lyrics)
    has_structure = len(draft.structure) >= 3
    has_arrangement = bool(draft.arrangement.get("instruments"))
    has_production = bool(draft.production.get("suno_style_tags") or draft.production.get("suno_style_string"))
    compliance_pass = sum(1 for v in draft.compliance.values() if v is True)
    compliance_total = max(len(draft.compliance), 1)
    compliance_ratio = compliance_pass / compliance_total

    s.melody_catchiness = 5.0 if has_lyrics else 2.0
    s.lyric_quality = 5.0 if has_lyrics else 2.0
    s.harmonic_sophistication = 5.0 if has_structure else 3.0
    s.structural_coherence = min(8.0, 3.0 + len(draft.structure) * 0.5)
    s.production_direction = 6.0 if has_production else 3.0
    s.genre_authenticity = 5.0 if has_arrangement else 3.0

    s.overall = round(
        s.melody_catchiness * 0.20
        + s.lyric_quality * 0.20
        + s.genre_authenticity * 0.20
        + s.structural_coherence * 0.15
        + s.production_direction * 0.15
        + s.harmonic_sophistication * 0.10,
        1,
    )

    if compliance_ratio < 0.7:
        s.overall = min(s.overall, 5.0)
        notes.append(f"Compliance ratio thấp ({compliance_pass}/{compliance_total})")

    if s.overall >= 7.5:
        verdict = "RELEASE"
    elif s.overall >= 5.0:
        verdict = "REVISE"
    else:
        verdict = "REJECT"

    if not has_lyrics:
        notes.append("Thiếu lyrics")
    if not has_arrangement:
        notes.append("Thiếu arrangement instruments")
    if not has_production:
        notes.append("Thiếu production/style tags")

    return QualityEvaluation(
        scores=s,
        verdict=verdict,  # type: ignore[arg-type]
        feedback="Heuristic evaluation (no LLM). " + "; ".join(notes) if notes else "Heuristic evaluation (no LLM).",
        revision_notes="; ".join(notes) if verdict != "RELEASE" else "",
    )
