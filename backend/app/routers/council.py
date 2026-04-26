"""Council endpoints: brief intake, composition, and persona introspection."""
from __future__ import annotations

from fastapi import APIRouter

from app.schemas import Brief, SongDraft
from app.services import council as council_svc
from app.services import store

router = APIRouter(prefix="/council", tags=["council"])


@router.get("/personas")
def list_personas() -> list[dict[str, object]]:
    return [
        {
            "name": p.name,
            "role": p.role,
            "expertise_tags": list(p.expertise_tags),
            "system_prompt": p.system_prompt,
        }
        for p in council_svc.COUNCIL_PERSONAS
    ]


@router.post("/brief")
def brief_intake(brief: Brief) -> dict[str, object]:
    return {
        "brief": brief,
        "clarifying_questions": council_svc.clarifying_questions(brief),
    }


@router.post("/compose", response_model=SongDraft)
def compose(brief: Brief) -> SongDraft:
    draft = council_svc.compose(brief)
    return store.save(draft)
