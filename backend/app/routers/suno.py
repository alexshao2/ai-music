"""Suno bridge endpoints."""
from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, HTTPException

from app.schemas import SunoPrompt
from app.services import store
from app.services import suno as suno_svc

router = APIRouter(prefix="/suno", tags=["suno"])

SUNO_CREATE_URL = "https://suno.com/create"


@router.get("/prompt/{draft_id}", response_model=SunoPrompt)
def build_prompt(draft_id: str) -> SunoPrompt:
    d = store.get(draft_id)
    if not d:
        raise HTTPException(status_code=404, detail="Draft not found")
    prompt = suno_svc.build_prompt(d)
    # Persist back for convenience.
    d.suno_prompt = prompt.model_dump()
    store.save(d)
    return prompt


@router.get("/launch/{draft_id}")
def launch_url(draft_id: str) -> dict[str, str]:
    """Returns the Suno create URL plus the prompt the frontend should put on
    the user's clipboard. Suno does not (yet) accept arbitrary query-string
    prefill for guests, so the frontend is responsible for the clipboard step.
    """
    d = store.get(draft_id)
    if not d:
        raise HTTPException(status_code=404, detail="Draft not found")
    prompt = suno_svc.build_prompt(d)
    return {
        "open_url": SUNO_CREATE_URL,
        "title": prompt.title,
        "style": prompt.style,
        "lyrics": prompt.lyrics,
        "preview_query": f"{SUNO_CREATE_URL}?style={quote(prompt.style)}",
    }
