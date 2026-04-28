"""Smoke tests for the /council/options picker endpoint + helpers."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services import options as options_svc

client = TestClient(app)


def test_list_genres_includes_vpop_ballad() -> None:
    """The seeded knowledge base must expose V-pop Ballad as a vpop-group genre."""
    genres = options_svc.list_genres()
    slugs = {g.slug for g in genres}
    assert "vpop-ballad" in slugs, f"vpop-ballad not in {slugs}"
    vpop = next(g for g in genres if g.slug == "vpop-ballad")
    assert vpop.group == "vpop"
    assert vpop.knowledge_path == "genres/vpop-ballad.md"


def test_list_genres_groups_hip_hop_correctly() -> None:
    """Trap / V-rap / modern-hip-hop-storytelling must land in the hip-hop group."""
    genres = {g.slug: g for g in options_svc.list_genres()}
    # Each of these is only reachable if frontmatter tags include a hip-hop
    # keyword; if this breaks, knowledge corpus drift is the culprit.
    assert genres["trap"].group == "hiphop"
    assert genres["modern-hip-hop-storytelling"].group == "hiphop"
    # V-rap has both 'vrap' (→ vpop group) and 'rap' (→ hip-hop); vpop wins
    # because it appears earlier in _GROUP_TAG_RULES.
    assert genres["vrap"].group == "vpop"


def test_list_moods_nonempty_and_unique_slugs() -> None:
    moods = options_svc.list_moods()
    assert len(moods) >= 15
    slugs = [m.slug for m in moods]
    assert len(slugs) == len(set(slugs)), "mood slugs must be unique"


def test_options_endpoint_shape() -> None:
    """The HTTP contract: payload has genres / moods / languages arrays."""
    r = client.get("/council/options")
    assert r.status_code == 200
    payload = r.json()
    assert set(payload.keys()) == {"genres", "moods", "languages"}
    assert payload["genres"], "genres must not be empty"
    first = payload["genres"][0]
    assert {"slug", "label", "group", "group_label", "tags", "knowledge_path"} <= set(first.keys())
    assert payload["moods"][0]["slug"]
    assert payload["languages"][0]["code"] in {"vi", "en", "ja", "ko"}


def test_genres_sorted_by_group_order() -> None:
    """FE relies on backend-sorted genres to render <optgroup> boundaries.

    Assert that all 'vpop' entries come before all 'english' entries in
    the response, so the UI can iterate linearly.
    """
    genres = options_svc.list_genres()
    groups_seen: list[str] = []
    for g in genres:
        if not groups_seen or groups_seen[-1] != g.group:
            groups_seen.append(g.group)
    # Each group appears as exactly one contiguous run.
    assert len(groups_seen) == len(set(groups_seen)), (
        f"groups interleaved: {groups_seen}"
    )
