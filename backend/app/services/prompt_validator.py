"""Validate Suno prompt quality before user paste.

Catches common issues: style string too long/short, missing tempo/key,
lyrics missing section tags, genre parameter mismatches against the
knowledge base genre cookbooks.
"""
from __future__ import annotations

import re

from app.schemas import PromptValidation, SongDraft
from app.services import knowledge as knowledge_svc


def validate(draft: SongDraft) -> PromptValidation:
    """Run all prompt-level checks and return a PromptValidation."""
    issues: list[str] = []
    suggestions: list[str] = []

    _check_style(draft, issues, suggestions)
    _check_lyrics(draft, issues, suggestions)
    _check_genre_params(draft, issues, suggestions)
    _check_compliance(draft, issues, suggestions)

    score = max(0.0, min(10.0, 10.0 - len(issues) * 1.5))
    return PromptValidation(
        valid=len(issues) == 0,
        score=round(score, 1),
        issues=issues,
        suggestions=suggestions,
    )


def _check_style(
    draft: SongDraft,
    issues: list[str],
    suggestions: list[str],
) -> None:
    if draft.suno_output is None:
        issues.append("SunoOutput chưa được tạo — không có style string")
        return

    style = draft.suno_output.style
    if len(style) > 200:
        issues.append(
            f"Style string quá dài ({len(style)} chars, max 200)"
        )
    if len(style) < 40:
        issues.append(
            f"Style string quá ngắn ({len(style)} chars, nên >= 60 để Suno hiểu rõ)"
        )
        suggestions.append("Thêm tempo, key, instruments, vocal style vào style string")
    if "bpm" not in style.lower() and not re.search(r"\d{2,3}\s*bpm", style, re.I):
        suggestions.append("Nên có BPM trong style string để Suno render đúng tempo")
    if not any(k in style.lower() for k in ("major", "minor", "lydian", "mixolydian", "dorian")):
        suggestions.append("Nên có key/mode trong style string")


def _check_lyrics(
    draft: SongDraft,
    issues: list[str],
    suggestions: list[str],
) -> None:
    lyrics = ""
    if draft.suno_output is not None:
        lyrics = draft.suno_output.lyrics
    if not lyrics:
        if draft.lyrics:
            suggestions.append("Draft có lyrics nhưng SunoOutput chưa format — cần build_prompt()")
        else:
            issues.append("Không có lyrics")
        return

    has_section_tags = bool(re.search(r"\[(Verse|Chorus|Bridge|Intro|Outro|Pre-Chorus)]", lyrics))
    if not has_section_tags:
        issues.append(
            "Lyrics thiếu section tags [Verse]/[Chorus] — Suno sẽ không biết structure"
        )

    line_count = len([line for line in lyrics.split("\n") if line.strip()])
    if line_count < 6:
        issues.append(f"Lyrics quá ngắn ({line_count} dòng, nên >= 10)")


def _check_genre_params(
    draft: SongDraft,
    issues: list[str],
    suggestions: list[str],
) -> None:
    """Cross-check tempo against genre cookbook ranges from knowledge base."""
    genre_query = draft.brief.genre.lower()
    chunks = knowledge_svc.search(genre_query, k=2)
    if not chunks:
        return

    for chunk in chunks:
        excerpt = chunk.excerpt.lower()
        tempo_ranges = re.findall(r"(\d{2,3})\s*[-–]\s*(\d{2,3})\s*bpm", excerpt)
        if not tempo_ranges:
            continue

        low = int(tempo_ranges[0][0])
        high = int(tempo_ranges[0][1])
        if draft.tempo_bpm < low - 10 or draft.tempo_bpm > high + 10:
            issues.append(
                f"Tempo {draft.tempo_bpm} BPM ngoài range genre "
                f"({low}-{high} BPM theo {chunk.title})"
            )
        break


def _check_compliance(
    draft: SongDraft,
    issues: list[str],
    suggestions: list[str],
) -> None:
    """Flag compliance check failures from the Critic."""
    if not draft.compliance:
        suggestions.append("Chưa có compliance checks — chạy council với LLM để có checks")
        return

    failed = [k for k, v in draft.compliance.items() if v is False]
    if failed:
        issues.append(
            f"Compliance checks thất bại: {', '.join(failed)}"
        )
