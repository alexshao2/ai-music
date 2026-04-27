"""Studio endpoints: list / fetch / patch / evaluate song drafts."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.schemas import PromptValidation, QualityEvaluation, SongDraft
from app.services import audio_evaluator, prompt_validator, store

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


@router.post("/drafts/{draft_id}/evaluate", response_model=QualityEvaluation)
def evaluate_draft(draft_id: str) -> QualityEvaluation:
    """Run an A&R quality evaluation on a draft.

    Uses the LLM when configured; falls back to heuristic scoring.
    The result is persisted on the draft's ``evaluation`` field.
    """
    d = store.get(draft_id)
    if not d:
        raise HTTPException(status_code=404, detail="Draft not found")
    evaluation = audio_evaluator.evaluate_draft(d)
    d.evaluation = evaluation
    store.save(d)
    return evaluation


@router.get("/drafts/{draft_id}/quality", response_model=QualityEvaluation)
def get_quality(draft_id: str) -> QualityEvaluation:
    """Return the most recent quality evaluation for a draft."""
    d = store.get(draft_id)
    if not d:
        raise HTTPException(status_code=404, detail="Draft not found")
    if d.evaluation is None:
        raise HTTPException(status_code=404, detail="No evaluation yet — POST /evaluate first")
    return d.evaluation


@router.post("/drafts/{draft_id}/validate-prompt", response_model=PromptValidation)
def validate_prompt(draft_id: str) -> PromptValidation:
    """Validate the Suno prompt before the user pastes it."""
    d = store.get(draft_id)
    if not d:
        raise HTTPException(status_code=404, detail="Draft not found")
    return prompt_validator.validate(d)
