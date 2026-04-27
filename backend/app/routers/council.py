"""Council endpoints: brief intake, composition, and persona introspection."""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator, Iterator
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.schemas import Brief, SongDraft
from app.services import council as council_svc
from app.services import store

router = APIRouter(prefix="/council", tags=["council"])

log = logging.getLogger(__name__)

# How often the SSE stream emits a keepalive comment while a persona is busy.
# Cloudflare Tunnel / CF edge close idle HTTP responses around the 100s mark;
# each council persona can run for 120s+ on slow routers, so the wait between
# real events routinely exceeds that threshold. Sending a comment well under
# the limit keeps the connection alive without affecting the UI.
SSE_KEEPALIVE_SECONDS = 15.0
_KEEPALIVE_FRAME = b": keepalive\n\n"


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

    SSE comment keepalives (``: keepalive\\n\\n``) are injected every
    :data:`SSE_KEEPALIVE_SECONDS` while a persona is still thinking so the
    connection stays open through Cloudflare / reverse proxies — real events
    would otherwise be silent for 120s+ per persona on slow LLM routers.
    """
    return StreamingResponse(
        _stream_with_keepalive(brief, refine=not fast),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _sync_event_stream(brief: Brief, *, refine: bool) -> Iterator[bytes]:
    """Drive the (synchronous) council generator and yield SSE-encoded bytes.

    Factored out so the async wrapper below can run it in a worker thread
    without having to know anything about council internals.
    """
    for event in council_svc.compose_stream(brief, refine=refine):
        payload: dict[str, Any] = dict(event)
        if event.get("type") == "draft":
            draft: SongDraft = event["draft"]  # type: ignore[assignment]
            stored = store.save(draft)
            payload["draft"] = stored.model_dump(mode="json")
        yield _sse(payload)
    yield _sse({"type": "done"})


async def _stream_with_keepalive(
    brief: Brief, *, refine: bool
) -> AsyncIterator[bytes]:
    """Bridge the sync council generator to async with periodic keepalives.

    Runs :func:`_sync_event_stream` in a worker thread and pushes its frames
    onto an ``asyncio.Queue``. The consumer here either forwards a real frame
    or — if nothing arrives within ``SSE_KEEPALIVE_SECONDS`` — emits a
    ``: keepalive\\n\\n`` comment, which SSE clients ignore but proxies see as
    fresh bytes.
    """
    queue: asyncio.Queue[bytes | BaseException | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def producer() -> None:
        try:
            for frame in _sync_event_stream(brief, refine=refine):
                loop.call_soon_threadsafe(queue.put_nowait, frame)
        except BaseException as exc:  # noqa: BLE001
            log.exception("council compose stream producer crashed")
            loop.call_soon_threadsafe(queue.put_nowait, exc)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    producer_task = loop.run_in_executor(None, producer)
    try:
        while True:
            try:
                item = await asyncio.wait_for(
                    queue.get(), timeout=SSE_KEEPALIVE_SECONDS
                )
            except TimeoutError:
                yield _KEEPALIVE_FRAME
                continue
            if item is None:
                return
            if isinstance(item, BaseException):
                # Surface the failure to the client as a structured SSE event
                # rather than dropping the connection with a 500 mid-stream.
                yield _sse({"type": "error", "message": str(item)})
                return
            yield item
    finally:
        # Make sure the worker thread is done before we let FastAPI close the
        # response, otherwise a late `put_nowait` would hit a dead loop.
        with contextlib.suppress(Exception):
            await producer_task


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
