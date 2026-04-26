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


def test_knowledge_search():
    # Knowledge base should have at least a few seeded docs.
    r = client.get("/knowledge/topics")
    assert r.status_code == 200
    assert len(r.json()) >= 5
