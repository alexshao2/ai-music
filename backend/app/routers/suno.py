"""Suno bridge endpoints."""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, HTTPException

from app.schemas import SunoPrompt
from app.services import store
from app.services import suno as suno_svc
from app.services import suno_autofill as suno_autofill_svc

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


@router.post("/autofill/{draft_id}")
def autofill(draft_id: str, wait: bool = True, timeout_sec: int = 180) -> dict[str, Any]:
    """Drive the user's logged-in Suno tab via CDP and submit the draft.

    Query params:
      wait=true (default)  — block until a new song row appears in My Workspace.
      timeout_sec=180      — max time to wait for completion.

    Returns ``{ submitted, title, style, lyrics_chars, suno_url, note }``. ``suno_url``
    is the song share URL when ``wait=true``, otherwise null.
    """
    d = store.get(draft_id)
    if not d:
        raise HTTPException(status_code=404, detail="Draft not found")
    try:
        result = suno_autofill_svc.autofill_and_generate(
            d, wait_for_song=wait, timeout_sec=timeout_sec
        )
    except suno_autofill_svc.SunoAutofillError as exc:
        log.warning("Suno autofill error: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        log.exception("Suno autofill crashed")
        raise HTTPException(status_code=500, detail=f"Autofill crashed: {exc}") from exc
    return {
        "submitted": result.submitted,
        "title": result.title,
        "style": result.style,
        "lyrics_chars": result.lyrics_chars,
        "suno_url": result.suno_url,
        "note": result.note,
    }
