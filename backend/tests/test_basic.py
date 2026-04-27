"""Smoke tests for the AI Music backend."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import Brief

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "ai-music"
    assert "/council" in body["endpoints"]


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_personas():
    r = client.get("/council/personas")
    assert r.status_code == 200
    names = {p["name"] for p in r.json()}
    assert {"Music Theorist", "Composer", "Lyricist", "Arranger", "Producer", "A&R Critic"} <= names


def test_brief_intake():
    r = client.post(
        "/council/brief",
        json=Brief(mood="hoài niệm", genre="indie folk", language="vi").model_dump(),
    )
    assert r.status_code == 200
    assert r.json()["clarifying_questions"]


def test_compose_and_suno():
    r = client.post(
        "/council/compose",
        json=Brief(mood="hoài niệm", genre="ballad", language="vi").model_dump(),
    )
    assert r.status_code == 200
    draft = r.json()
    assert draft["id"]
    assert len(draft["council_log"]) == 6
    assert draft["key"]
    assert draft["tempo_bpm"] > 0

    r2 = client.get(f"/suno/prompt/{draft['id']}")
    assert r2.status_code == 200
    prompt = r2.json()
    assert prompt["style"]
    assert "[" in prompt["lyrics"]  # contains section markers


def test_compose_stream_stub():
    """Stub-mode streaming should emit one started+completed per persona,
    then a draft event with the full SongDraft, then a terminal done."""
    import json as _j

    body = Brief(mood="hoài niệm", genre="ballad", language="vi").model_dump()
    with client.stream("POST", "/council/compose/stream", json=body) as r:
        assert r.status_code == 200
        events: list[dict] = []
        for line in r.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            events.append(_j.loads(line[len("data: "):]))

    # Order: started/completed for 6 personas (12 events) + draft + done.
    types = [e["type"] for e in events]
    started = [e for e in events if e["type"] == "persona_started"]
    completed = [e for e in events if e["type"] == "persona_completed"]
    drafts = [e for e in events if e["type"] == "draft"]
    assert len(started) == 6
    assert len(completed) == 6
    assert len(drafts) == 1
    assert types[-1] == "done"
    # Each completed event references a persona name and a non-empty message.
    for e in completed:
        assert e["name"] and e["message"]
    # Draft payload is JSON-serialisable and has the same id you can fetch back.
    draft = drafts[0]["draft"]
    assert draft["id"] and len(draft["council_log"]) == 6
    fetched = client.get(f"/studio/drafts/{draft['id']}")
    assert fetched.status_code == 200


def test_compose_stream_emits_keepalive_on_slow_producer(monkeypatch):
    """SSE keepalive comments must flow when the council generator stalls.

    Reproduces the Cloudflare Tunnel issue where personas taking 100s+ to
    emit a real event caused the edge to drop the HTTP/2 stream. We stub
    `council_svc.compose_stream` to sleep longer than the keepalive interval
    and verify at least one ``: keepalive`` comment appears before the next
    real event.
    """
    import time

    from app.routers import council as router_mod
    from app.services import council as council_svc

    def slow_events():
        yield {"type": "persona_started", "role": "theorist", "name": "Music Theorist", "index": 0, "total": 1}
        time.sleep(0.3)  # > 3x SSE_KEEPALIVE_SECONDS below, forces keepalives
        yield {"type": "persona_completed", "role": "theorist", "name": "Music Theorist", "message": "ok", "contributions": {}}

    monkeypatch.setattr(council_svc, "compose_stream", lambda _brief, refine=True: slow_events())
    monkeypatch.setattr(router_mod, "SSE_KEEPALIVE_SECONDS", 0.08)

    body = Brief(mood="hoài niệm", genre="ballad", language="vi").model_dump()
    with client.stream("POST", "/council/compose/stream", json=body) as r:
        assert r.status_code == 200
        raw = b"".join(r.iter_bytes()).decode("utf-8", errors="replace")

    assert ": keepalive" in raw, "SSE keepalive comment missing — CF will drop long streams"
    assert '"type": "persona_completed"' in raw
    # Keepalive must arrive between started and completed, not only at the end.
    started_at = raw.find("persona_started")
    keepalive_at = raw.find(": keepalive")
    completed_at = raw.find("persona_completed", started_at + 1)
    assert started_at < keepalive_at < completed_at


def test_compose_stream_surfaces_producer_exception(monkeypatch):
    """Exceptions in the sync generator should become a structured error event,
    not a torn HTTP/2 stream."""
    from app.services import council as council_svc

    def boom(_brief, refine=True):
        yield {"type": "persona_started", "role": "theorist", "name": "T", "index": 0, "total": 1}
        raise RuntimeError("persona explosion")

    monkeypatch.setattr(council_svc, "compose_stream", boom)

    body = Brief(mood="x", genre="y", language="vi").model_dump()
    with client.stream("POST", "/council/compose/stream", json=body) as r:
        assert r.status_code == 200
        raw = b"".join(r.iter_bytes()).decode("utf-8", errors="replace")

    assert '"type": "error"' in raw
    assert "persona explosion" in raw


def test_knowledge_search():
    # Knowledge base should have at least a few seeded docs.
    r = client.get("/knowledge/topics")
    assert r.status_code == 200
    assert len(r.json()) >= 5
