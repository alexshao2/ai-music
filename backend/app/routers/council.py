"""Council endpoints: brief intake, composition, and persona introspection."""
from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

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
def compose(brief: Brief, fast: bool = False) -> SongDraft:
    """Run the council and return a SongDraft.

    Query params:
      fast=true  — skip the post-Critic refinement pass (~25% faster, less polished).
    """
    draft = council_svc.compose(brief, refine=not fast)
    return store.save(draft)


@router.post("/compose/stream")
def compose_stream(brief: Brief, fast: bool = False) -> StreamingResponse:
    """Run the council and stream events as Server-Sent Events.

    Each event is a JSON object on a single line, prefixed with ``data: ``.
    See ``council_svc.compose_stream`` for the event shapes. The final ``draft``
    event also persists the draft to the store and includes its ``id``.
    """

    def event_stream() -> Iterator[bytes]:
        for event in council_svc.compose_stream(brief, refine=not fast):
            payload: dict[str, Any] = dict(event)
            if event.get("type") == "draft":
                draft: SongDraft = event["draft"]  # type: ignore[assignment]
                stored = store.save(draft)
                payload["draft"] = stored.model_dump(mode="json")
            yield _sse(payload)
        yield _sse({"type": "done"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/compose/quality", response_model=SongDraft)
def compose_quality(
    brief: Brief,
    target_score: float = Query(default=7.5, ge=0, le=10),
    max_revisions: int = Query(default=2, ge=0, le=10),
) -> SongDraft:
    """Compose with quality gate: auto-revise until score >= target.

    Query params:
      target_score  — minimum overall score to pass (default 7.5).
      max_revisions — maximum extra revision attempts (default 2).
    """
    draft = council_svc.compose_with_quality_gate(
        brief, target_score=target_score, max_revisions=max_revisions,
    )
    return store.save(draft)


def _sse(payload: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode()
