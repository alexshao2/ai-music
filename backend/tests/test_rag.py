"""Tests for M1 RAG: chunking, vector store, and search integration."""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.services.knowledge import _Doc, all_chunks, chunk_doc
from app.services.vector_store import Chunk, VectorStore, corpus_hash, embedding_config_hash

client = TestClient(app)


# ---------------------------------------------------------------------------
# Chunking tests
# ---------------------------------------------------------------------------

class TestChunking:
    def _doc(self, body: str, title: str = "Test Doc", path: str = "test.md") -> _Doc:
        return _Doc(path=path, title=title, tags=("test",), level="beginner", body=body)

    def test_no_headings_returns_single_chunk(self) -> None:
        doc = self._doc("This is a simple document with no headings.\nLine two.\nLine three.")
        chunks = chunk_doc(doc)
        assert len(chunks) == 1
        assert chunks[0].heading == "Test Doc"
        assert "simple document" in chunks[0].body

    def test_split_by_h2(self) -> None:
        doc = self._doc(
            "Preamble text that is long enough to be its own chunk (over forty chars).\n\n"
            "## Section One\nContent of section one with enough text to stand alone here.\n\n"
            "## Section Two\nContent of section two with enough text to stand alone here too."
        )
        chunks = chunk_doc(doc)
        headings = [c.heading for c in chunks]
        assert "Section One" in headings
        assert "Section Two" in headings

    def test_split_by_h3(self) -> None:
        doc = self._doc(
            "### Sub Section A\nContent A is long enough to be its own chunk passage.\n\n"
            "### Sub Section B\nContent B is long enough to be its own chunk passage too."
        )
        chunks = chunk_doc(doc)
        assert len(chunks) >= 2

    def test_tiny_sections_merged(self) -> None:
        doc = self._doc(
            "## Big Section\n"
            "Content that is definitely long enough to stand alone as a chunk.\n\n"
            "## Tiny\nAbc"
        )
        chunks = chunk_doc(doc)
        # "Tiny" with only "Abc" (3 chars < 40) should merge into previous
        assert all("Tiny" not in c.heading for c in chunks)

    def test_empty_body(self) -> None:
        doc = self._doc("")
        assert chunk_doc(doc) == []

    def test_preamble_too_short_skipped(self) -> None:
        doc = self._doc(
            "Hi\n\n"
            "## Real Section\nThis section has enough body content to be a real chunk."
        )
        chunks = chunk_doc(doc)
        # Preamble "Hi" is < 40 chars, should be skipped
        assert chunks[0].heading == "Real Section"

    def test_chunk_inherits_doc_metadata(self) -> None:
        doc = self._doc(
            "## Section\nBody text that is long enough for a standalone chunk.",
            title="My Song",
            path="genres/pop.md",
        )
        chunks = chunk_doc(doc)
        assert chunks[0].doc_path == "genres/pop.md"
        assert chunks[0].doc_title == "My Song"
        assert chunks[0].doc_tags == ("test",)

    def test_text_for_embedding(self) -> None:
        chunk = Chunk(
            doc_path="test.md",
            doc_title="Big Title",
            doc_tags=("harmony", "pop"),
            doc_level="beginner",
            heading="Chord Progressions",
            body="I-V-vi-IV is the most common pop progression.",
        )
        text = chunk.text_for_embedding
        assert "Big Title" in text
        assert "Chord Progressions" in text
        assert "harmony" in text
        assert "I-V-vi-IV" in text

    def test_all_chunks_returns_chunks_from_all_docs(self) -> None:
        chunks = all_chunks()
        # With 82 knowledge files, we should get many chunks
        assert len(chunks) >= 50
        # Should have chunks from different doc paths
        paths = {c.doc_path for c in chunks}
        assert len(paths) >= 10


# ---------------------------------------------------------------------------
# Vector store tests
# ---------------------------------------------------------------------------

class TestVectorStore:
    def _make_chunks(self, n: int = 5) -> list[Chunk]:
        return [
            Chunk(
                doc_path=f"doc{i}.md",
                doc_title=f"Doc {i}",
                doc_tags=("test",),
                doc_level=None,
                heading=f"Section {i}",
                body=f"Content of section {i} with some text.",
            )
            for i in range(n)
        ]

    def _random_embeddings(self, n: int, dim: int = 64) -> list[list[float]]:
        rng = np.random.default_rng(42)
        vecs = rng.standard_normal((n, dim)).astype(np.float32)
        return [v.tolist() for v in vecs]

    def test_set_embeddings_and_search(self) -> None:
        chunks = self._make_chunks(10)
        vecs = self._random_embeddings(10, dim=32)
        store = VectorStore(chunks=chunks)
        store.set_embeddings(vecs)
        assert store.is_built
        assert store.size == 10

        results = store.search(vecs[3], k=3)
        assert len(results) == 3
        # The query is exactly vec[3], so index 3 should be the top match
        scores, indices = zip(*results, strict=True)
        assert 3 in indices
        assert all(0 <= s <= 1.01 for s in scores)

    def test_search_empty_store(self) -> None:
        store = VectorStore()
        assert store.search([1.0, 0.0, 0.0], k=3) == []

    def test_search_zero_query(self) -> None:
        chunks = self._make_chunks(3)
        vecs = self._random_embeddings(3, dim=8)
        store = VectorStore(chunks=chunks)
        store.set_embeddings(vecs)
        assert store.search([0.0] * 8, k=2) == []

    def test_save_and_load(self) -> None:
        chunks = self._make_chunks(5)
        vecs = self._random_embeddings(5, dim=16)
        store = VectorStore(chunks=chunks, stored_hash="abc123")
        store.set_embeddings(vecs)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_index"
            store.save(path)
            loaded = VectorStore.load(path)

        assert loaded is not None
        assert loaded.size == 5
        assert loaded.chunks[0].doc_path == "doc0.md"
        assert loaded.stored_hash == "abc123"
        # Search should work on loaded store
        results = loaded.search(vecs[0], k=2)
        assert len(results) == 2

    def test_stale_hash_not_reused(self) -> None:
        """Index with wrong hash should not match a different corpus hash."""
        chunks = self._make_chunks(3)
        vecs = self._random_embeddings(3, dim=8)
        store = VectorStore(chunks=chunks, stored_hash="old_hash")
        store.set_embeddings(vecs)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_index"
            store.save(path)
            loaded = VectorStore.load(path)

        assert loaded is not None
        assert loaded.stored_hash == "old_hash"
        # Should NOT match a new corpus hash
        assert loaded.stored_hash != "new_hash"

    def test_load_nonexistent(self) -> None:
        assert VectorStore.load(Path("/tmp/nonexistent_index_xyz")) is None

    def test_corpus_hash_changes(self) -> None:
        chunks_a = self._make_chunks(3)
        chunks_b = self._make_chunks(4)
        h_a = corpus_hash(chunks_a)
        h_b = corpus_hash(chunks_b)
        assert h_a != h_b
        # Same chunks → same hash
        assert corpus_hash(chunks_a) == h_a

    def test_k_larger_than_store(self) -> None:
        chunks = self._make_chunks(3)
        vecs = self._random_embeddings(3, dim=8)
        store = VectorStore(chunks=chunks)
        store.set_embeddings(vecs)
        results = store.search(vecs[0], k=100)
        assert len(results) == 3

    def test_embedding_config_hash_changes_with_model(self) -> None:
        h1 = embedding_config_hash("text-embedding-3-small", "https://api.openai.com/v1", 1536)
        h2 = embedding_config_hash("bge-large-en", "https://api.openai.com/v1", 1536)
        h3 = embedding_config_hash("text-embedding-3-small", "https://other.example/v1", 1536)
        h4 = embedding_config_hash("text-embedding-3-small", "https://api.openai.com/v1", 1024)
        h5 = embedding_config_hash("text-embedding-3-small", "https://api.openai.com/v1", None)
        assert h1 != h2  # model changed
        assert h1 != h3  # base_url changed
        assert h1 != h4  # dimensions changed
        assert h1 != h5  # dim unset vs set
        # Same inputs → same hash (deterministic)
        assert h1 == embedding_config_hash(
            "text-embedding-3-small", "https://api.openai.com/v1", 1536
        )

    def test_config_hash_persists_across_save_load(self) -> None:
        """Saved index must round-trip config_hash so cache can be invalidated."""
        chunks = self._make_chunks(3)
        vecs = self._random_embeddings(3, dim=8)
        store = VectorStore(chunks=chunks, stored_hash="corpus-abc", config_hash="cfg-xyz")
        store.set_embeddings(vecs)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_index"
            store.save(path)
            loaded = VectorStore.load(path)

        assert loaded is not None
        assert loaded.stored_hash == "corpus-abc"
        assert loaded.config_hash == "cfg-xyz"


# ---------------------------------------------------------------------------
# Search integration tests (keyword fallback — no API key in CI)
# ---------------------------------------------------------------------------

class TestSearchIntegration:
    def test_keyword_search_still_works(self) -> None:
        results = client.get("/knowledge/search?q=ballad").json()
        assert len(results) > 0
        assert any("ballad" in r["title"].lower() for r in results)

    def test_keyword_search_genre(self) -> None:
        results = client.get("/knowledge/search?q=reggae").json()
        assert len(results) > 0

    def test_keyword_search_empty_query(self) -> None:
        results = client.get("/knowledge/search?q=").json()
        assert results == []

    def test_rebuild_index_without_key(self) -> None:
        r = client.post("/knowledge/rebuild-index")
        assert r.status_code == 200
        data = r.json()
        assert data["docs"] > 0
        # Without API key, vector_search should be False
        assert data["vector_search"] is False

    def test_topics_still_work(self) -> None:
        r = client.get("/knowledge/topics")
        assert r.status_code == 200
        assert len(r.json()) >= 50

    def test_existing_council_compose_unbroken(self) -> None:
        """Ensure the council compose still works after RAG upgrade."""
        from app.schemas import Brief

        r = client.post(
            "/council/compose",
            json=Brief(mood="vui", genre="pop", language="vi").model_dump(),
        )
        assert r.status_code == 200
        draft = r.json()
        assert draft["id"]
        assert len(draft["council_log"]) == 6
