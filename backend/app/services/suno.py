"""Build Suno prompts from a Song Draft."""
from __future__ import annotations

from typing import Any

from app.schemas import SongDraft, SunoPrompt

_SECTION_LABEL = {
    "intro": "Intro",
    "verse": "Verse",
    "pre_chorus": "Pre-Chorus",
    "chorus": "Chorus",
    "bridge": "Bridge",
    "outro": "Outro",
    "instrumental": "Instrumental",
}

# Suno's "style" field accepts ~200 chars before truncation.
SUNO_STYLE_LIMIT = 200


def _format_lyrics(draft: SongDraft) -> str:
    """Render lyrics with [Section] tags Suno understands.

    Walks the structure list in order and pulls the matching lyric block. Skips
    sections that have no lyric (intro/outro often). The lyric dict may key on
    plain section names (``chorus``) or numbered ones (``verse_1``, ``verse_2``).
    """
    lines: list[str] = []
    seen_verse = 0
    seen_chorus = 0
    for sec in draft.structure:
        label = _SECTION_LABEL.get(sec.section, sec.section.title())
        key_in_lyrics = sec.section
        if sec.section == "verse":
            seen_verse += 1
            key_in_lyrics = f"verse_{seen_verse}"
        elif sec.section == "chorus":
            seen_chorus += 1
            if seen_chorus == 1:
                key_in_lyrics = "chorus"
        body = (
            draft.lyrics.get(key_in_lyrics)
            or draft.lyrics.get(sec.section)
            or ""
        )
        if not body:
            continue
        lines.append(f"[{label}]")
        lines.append(body.strip())
        lines.append("")
    return "\n".join(lines).strip()


def _format_style(draft: SongDraft) -> str:
    """Build the Suno style string.

    Prefers the producer's curated ``suno_style_tags`` when available, then
    falls back to a derived list of (genre, mood, tempo, key, instruments,
    palette).
    """
    prod: dict[str, Any] = dict(draft.production or {})
    tags: list[str] = list(prod.get("suno_style_tags") or [])
    parts: list[str] = []

    if tags:
        parts.extend(str(t).strip() for t in tags if str(t).strip())
    else:
        instruments = list((draft.arrangement or {}).get("instruments") or [])
        palette = prod.get("sound_palette") or prod.get("palette") or ""
        derived = [
            draft.brief.genre,
            draft.brief.mood,
            f"{draft.tempo_bpm} BPM",
            draft.key,
            ", ".join(map(str, instruments)) if instruments else "",
            str(palette),
        ]
        parts = [p for p in derived if p]

    text = ", ".join(parts)
    return text[:SUNO_STYLE_LIMIT].rstrip(", ")


def build_prompt(draft: SongDraft) -> SunoPrompt:
    """Build the 3 Suno copy-paste blocks from a draft.

    Prefers the council-curated ``suno_output`` (Producer's curated style +
    Lyricist's marker-enhanced lyrics) when present, since that path applies
    the persona-level prompt engineering. Falls back to a derived style/lyric
    formatter for stub-only drafts.
    """
    if draft.suno_output is not None:
        style = draft.suno_output.style[:SUNO_STYLE_LIMIT].rstrip(", ")
        lyrics = draft.suno_output.lyrics or "[Instrumental]"
        return SunoPrompt(
            title=draft.suno_output.title or draft.title,
            style=style or _format_style(draft),
            lyrics=lyrics,
        )
    return SunoPrompt(
        title=draft.title,
        style=_format_style(draft),
        lyrics=_format_lyrics(draft) or "[Instrumental]",
    )
