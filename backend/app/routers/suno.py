"""Suno bridge endpoints (manual paste only — autofill removed)."""
from __future__ import annotations

import logging
from urllib.parse import quote

from fastapi import APIRouter, HTTPException

from app.schemas import SunoPrompt
from app.services import store
from app.services import suno as suno_svc

router = APIRouter(prefix="/suno", tags=["suno"])

log = logging.getLogger(__name__)

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
def launch_url(draft_id: str) -> dict[str, object]:
    """Returns the Suno create URL plus the prompt the frontend should put on
    the user's clipboard. Suno does not (yet) accept arbitrary query-string
    prefill for guests, so the frontend is responsible for the clipboard step.

    Also returns ``negative_tags`` and ``producer_brief`` when the council
    populated them, so the UI can show extra context next to the 3 copy
    blocks.
    """
    d = store.get(draft_id)
    if not d:
        raise HTTPException(status_code=404, detail="Draft not found")
    prompt = suno_svc.build_prompt(d)
    negative_tags: list[str] = []
    producer_brief = ""
    if d.suno_output is not None:
        negative_tags = list(d.suno_output.negative_tags)
        producer_brief = d.suno_output.producer_brief
    return {
        "open_url": SUNO_CREATE_URL,
        "title": prompt.title,
        "style": prompt.style,
        "lyrics": prompt.lyrics,
        "negative_tags": negative_tags,
        "producer_brief": producer_brief,
        "preview_query": f"{SUNO_CREATE_URL}?style={quote(prompt.style)}",
    }



