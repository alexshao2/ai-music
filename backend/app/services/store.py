"""In-memory + file-backed draft store. M5 will replace with SQLite."""
from __future__ import annotations

import json
from pathlib import Path

from app.schemas import SongDraft

_BASE = Path(__file__).resolve().parent.parent / "data" / "sessions"
_BASE.mkdir(parents=True, exist_ok=True)

_CACHE: dict[str, SongDraft] = {}


def save(draft: SongDraft) -> SongDraft:
    _CACHE[draft.id] = draft
    (_BASE / f"{draft.id}.json").write_text(
        json.dumps(draft.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return draft


def get(draft_id: str) -> SongDraft | None:
    if draft_id in _CACHE:
        return _CACHE[draft_id]
    p = _BASE / f"{draft_id}.json"
    if not p.exists():
        return None
    draft = SongDraft.model_validate_json(p.read_text(encoding="utf-8"))
    _CACHE[draft_id] = draft
    return draft


def list_all() -> list[SongDraft]:
    drafts: list[SongDraft] = []
    for p in sorted(_BASE.glob("*.json")):
        draft = get(p.stem)
        if draft:
            drafts.append(draft)
    return drafts
