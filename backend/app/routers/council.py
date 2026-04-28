"""Council endpoints: brief intake, composition, and persona introspection."""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.schemas import Brief, SongDraft
from app.services import council as council_svc
from app.services import options as options_svc
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


@router.get("/options")
def list_brief_options() -> dict[str, object]:
    """Predefined picker values for the brief form.

    Genres are derived from ``knowledge/genres/*.md`` so adding a cookbook
    automatically appears in the FE without code changes. Moods come from
    the curated list in :mod:`app.services.options`. Languages mirror the
    discrete values the council currently knows how to write in.
    """
    genres = [
        {
            "slug": g.slug,
            "label": g.label,
            "group": g.group,
            "group_label": options_svc.group_label(g.group),
            "tags": list(g.tags),
            "knowledge_path": g.knowledge_path,
        }
        for g in options_svc.list_genres()
    ]
    moods = [
        {
            "slug": m.slug,
            "label": m.label,
            "group": m.group,
            "keywords": list(m.keywords),
        }
        for m in options_svc.list_moods()
    ]
    languages = [
        {"code": "vi", "label": "Tiếng Việt"},
        {"code": "en", "label": "English"},
        {"code": "ja", "label": "日本語"},
        {"code": "ko", "label": "한국어"},
    ]
    return {"genres": genres, "moods": moods, "languages": languages}


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


@router.post("/compose/quality/stream")
def compose_quality_stream(
    brief: Brief,
    target_score: float = Query(default=7.5, ge=0, le=10),
    max_revisions: int = Query(default=2, ge=0, le=10),
    fast: bool = False,
) -> StreamingResponse:
    """Stream the council with an auto-revise quality gate.

    Like :func:`compose_stream` but wraps each council run in a
    ``while score < target`` loop (capped at ``max_revisions`` extra
    attempts). The frontend receives ``revision_started`` /
    ``revision_completed`` markers around each council pass plus an
    ``attempt`` field on every persona/refine event so it can group them.
    """
    return StreamingResponse(
        _quality_stream_with_keepalive(
            brief,
            target_score=target_score,
            max_revisions=max_revisions,
            refine=not fast,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


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


def _encode_council_events(
    events: Iterator[dict[str, Any]],
) -> Iterator[bytes]:
    """Encode a council event generator as SSE bytes, persisting any draft.

    Shared by both the plain compose stream and the quality-gated variant —
    both emit the same event shapes (with the latter adding ``revision_*``
    markers and an ``attempt`` field) and want the same store-save behaviour
    on the final ``draft`` event.
    """
    for event in events:
        payload: dict[str, Any] = dict(event)
        if event.get("type") == "draft":
            draft: SongDraft = event["draft"]  # type: ignore[assignment]
            stored = store.save(draft)
            payload["draft"] = stored.model_dump(mode="json")
        yield _sse(payload)
    yield _sse({"type": "done"})


def _sync_event_stream(brief: Brief, *, refine: bool) -> Iterator[bytes]:
    """Drive the synchronous compose generator and yield SSE-encoded bytes."""
    yield from _encode_council_events(
        council_svc.compose_stream(brief, refine=refine)
    )


def _sync_quality_event_stream(
    brief: Brief,
    *,
    target_score: float,
    max_revisions: int,
    refine: bool,
) -> Iterator[bytes]:
    """Drive the quality-gated compose generator and yield SSE-encoded bytes."""
    yield from _encode_council_events(
        council_svc.compose_quality_stream(
            brief,
            target_score=target_score,
            max_revisions=max_revisions,
            refine=refine,
        )
    )


async def _bytes_stream_with_keepalive(
    sync_iter_factory: Callable[[], Iterator[bytes]],
    *,
    log_label: str,
) -> AsyncIterator[bytes]:
    """Bridge any sync byte generator to async with periodic keepalives.

    Runs the factory in a worker thread and pushes its frames onto an
    ``asyncio.Queue``. The consumer here either forwards a real frame or — if
    nothing arrives within ``SSE_KEEPALIVE_SECONDS`` — emits a
    ``: keepalive\\n\\n`` comment, which SSE clients ignore but proxies see as
    fresh bytes. Cloudflare Tunnel and similar HTTP edges close idle responses
    around 100s; council persona turns can run 120s+ on slow LLM routers.
    """
    queue: asyncio.Queue[bytes | BaseException | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def producer() -> None:
        try:
            for frame in sync_iter_factory():
                loop.call_soon_threadsafe(queue.put_nowait, frame)
        except BaseException as exc:  # noqa: BLE001
            log.exception("%s producer crashed", log_label)
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


async def _stream_with_keepalive(
    brief: Brief, *, refine: bool
) -> AsyncIterator[bytes]:
    async for frame in _bytes_stream_with_keepalive(
        lambda: _sync_event_stream(brief, refine=refine),
        log_label="council compose stream",
    ):
        yield frame


async def _quality_stream_with_keepalive(
    brief: Brief,
    *,
    target_score: float,
    max_revisions: int,
    refine: bool,
) -> AsyncIterator[bytes]:
    async for frame in _bytes_stream_with_keepalive(
        lambda: _sync_quality_event_stream(
            brief,
            target_score=target_score,
            max_revisions=max_revisions,
            refine=refine,
        ),
        log_label="council quality stream",
    ):
        yield frame


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
