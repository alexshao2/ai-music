"""Studio endpoints: list / fetch / patch song drafts."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas import SongDraft
from app.services import store

router = APIRouter(prefix="/studio", tags=["studio"])


@router.get("/drafts", response_model=list[SongDraft])
def list_drafts() -> list[SongDraft]:
    return store.list_all()


@router.get("/drafts/{draft_id}", response_model=SongDraft)
def get_draft(draft_id: str) -> SongDraft:
    d = store.get(draft_id)
    if not d:
        raise HTTPException(status_code=404, detail="Draft not found")
    return d


@router.patch("/drafts/{draft_id}", response_model=SongDraft)
def patch_draft(draft_id: str, patch: dict[str, Any]) -> SongDraft:
    d = store.get(draft_id)
    if not d:
        raise HTTPException(status_code=404, detail="Draft not found")
    data = d.model_dump()
    # Shallow merge for top-level fields the client wants to update.
    for k, v in patch.items():
        if k in data:
            data[k] = v
    updated = SongDraft.model_validate(data)
    return store.save(updated)
