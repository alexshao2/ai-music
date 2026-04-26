"""Build Suno prompts from a Song Draft."""
from __future__ import annotations

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


def _format_lyrics(draft: SongDraft) -> str:
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
        body = draft.lyrics.get(key_in_lyrics) or draft.lyrics.get(sec.section) or ""
        if not body:
            continue
        lines.append(f"[{label}]")
        lines.append(body.strip())
        lines.append("")
    return "\n".join(lines).strip()


def _format_style(draft: SongDraft) -> str:
    instruments = draft.arrangement.get("instruments") or []
    palette = draft.production.get("palette") or ""
    parts = [
        draft.brief.genre,
        draft.brief.mood,
        f"{draft.tempo_bpm} BPM",
        draft.key,
        ", ".join(map(str, instruments)) if instruments else "",
        str(palette),
    ]
    text = ", ".join(p for p in parts if p)
    # Suno style field is typically capped at 200 chars.
    return text[:200]


def build_prompt(draft: SongDraft) -> SunoPrompt:
    return SunoPrompt(
        title=draft.title,
        style=_format_style(draft),
        lyrics=_format_lyrics(draft) or "[Instrumental]",
    )
