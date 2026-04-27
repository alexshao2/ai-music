"""Lightweight vector store using numpy cosine similarity.

At the current corpus size (~300–500 chunks from 80+ markdown files) brute-force
cosine similarity is sub-millisecond.  If the corpus grows past ~10 000 chunks,
swap for FAISS ``IndexFlatIP`` on normalized vectors for the same API.

Persistence: embeddings + metadata are saved as a single ``.npz`` archive so the
index survives server restarts without re-embedding.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A passage extracted from a knowledge markdown file."""

    doc_path: str
    doc_title: str
    doc_tags: tuple[str, ...]
    doc_level: str | None
    heading: str
    body: str
    char_offset: int = 0

    @property
    def text_for_embedding(self) -> str:
        """Concatenate title + heading + body for embedding."""
        parts = [self.doc_title]
        if self.heading and self.heading != self.doc_title:
            parts.append(self.heading)
        if self.doc_tags:
            parts.append(" ".join(self.doc_tags))
        parts.append(self.body[:2000])
        return "\n".join(parts)


@dataclass
class VectorStore:
    """In-memory vector index with numpy cosine similarity search."""

    chunks: list[Chunk] = field(default_factory=list)
    stored_hash: str = ""  # corpus hash at build time
    config_hash: str = ""  # embedding config hash (model|base_url|dim) at build time
    _embeddings: np.ndarray | None = None  # shape (n_chunks, dim)
    _norms: np.ndarray | None = None  # precomputed L2 norms

    @property
    def is_built(self) -> bool:
        return self._embeddings is not None and len(self.chunks) > 0

    @property
    def size(self) -> int:
        return len(self.chunks)

    def set_embeddings(self, vectors: list[list[float]]) -> None:
        """Set the embedding matrix from a list of float vectors."""
        mat = np.array(vectors, dtype=np.float32)
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-10)
        self._embeddings = mat / norms  # L2-normalize for cosine similarity
        self._norms = norms

    def search(self, query_vector: list[float], k: int = 5) -> list[tuple[float, int]]:
        """Return top-k (cosine_similarity, chunk_index) pairs, descending."""
        if self._embeddings is None or len(self.chunks) == 0:
            return []
        qv = np.array(query_vector, dtype=np.float32)
        qnorm = np.linalg.norm(qv)
        if qnorm < 1e-10:
            return []
        qv = qv / qnorm
        scores = self._embeddings @ qv  # cosine similarities
        top_k = min(k, len(self.chunks))
        if top_k >= len(self.chunks):
            # No need to partition — just sort everything
            idxs = np.argsort(-scores)[:top_k]
        else:
            idxs = np.argpartition(-scores, top_k)[:top_k]
            idxs = idxs[np.argsort(-scores[idxs])]
        return [(float(scores[i]), int(i)) for i in idxs]

    def save(self, path: Path) -> None:
        """Persist embeddings + chunk metadata to disk."""
        if self._embeddings is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        meta = [
            {
                "doc_path": c.doc_path,
                "doc_title": c.doc_title,
                "doc_tags": list(c.doc_tags),
                "doc_level": c.doc_level,
                "heading": c.heading,
                "body": c.body,
                "char_offset": c.char_offset,
            }
            for c in self.chunks
        ]
        meta_json = json.dumps(meta, ensure_ascii=False)
        np.savez_compressed(
            path,
            embeddings=self._embeddings,
            meta=np.array([meta_json]),
            corpus_hash=np.array([self.stored_hash]),
            config_hash=np.array([self.config_hash]),
        )
        log.info("Vector store saved to %s (%d chunks)", path, len(self.chunks))

    @classmethod
    def load(cls, path: Path) -> VectorStore | None:
        """Load a persisted index. Returns None if the file doesn't exist."""
        npz_path = path if str(path).endswith(".npz") else Path(f"{path}.npz")
        if not npz_path.exists():
            return None
        try:
            data = np.load(npz_path, allow_pickle=False)
            embeddings = data["embeddings"]
            meta_json = str(data["meta"][0])
            meta = json.loads(meta_json)
            chunks = [
                Chunk(
                    doc_path=m["doc_path"],
                    doc_title=m["doc_title"],
                    doc_tags=tuple(m["doc_tags"]),
                    doc_level=m.get("doc_level"),
                    heading=m["heading"],
                    body=m["body"],
                    char_offset=m.get("char_offset", 0),
                )
                for m in meta
            ]
            stored_hash = str(data["corpus_hash"][0]) if "corpus_hash" in data else ""
            config_hash = str(data["config_hash"][0]) if "config_hash" in data else ""
            store = cls(chunks=chunks, stored_hash=stored_hash, config_hash=config_hash)
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms = np.maximum(norms, 1e-10)
            store._embeddings = embeddings / norms
            store._norms = norms
            log.info(
                "Vector store loaded from %s (%d chunks, corpus=%s, config=%s)",
                npz_path, len(chunks), stored_hash[:8], config_hash[:8] or "n/a",
            )
            return store
        except Exception:
            log.exception("Failed to load vector store from %s", npz_path)
            return None


def corpus_hash(chunks: list[Chunk]) -> str:
    """Compute a hash of the chunk texts to detect corpus changes."""
    h = hashlib.sha256()
    for c in sorted(chunks, key=lambda x: (x.doc_path, x.char_offset)):
        h.update(c.text_for_embedding.encode())
    return h.hexdigest()[:16]


def embedding_config_hash(model: str, base_url: str | None, dimensions: int | None) -> str:
    """Hash the embedding configuration so a changed model/endpoint/dim invalidates
    a cached index even when chunk text is unchanged.

    Keeping this separate from ``corpus_hash`` makes the two failure modes —
    corpus drift vs. infra change — independently diagnosable in logs.
    """
    h = hashlib.sha256()
    h.update(f"{model}|{base_url or ''}|{dimensions or ''}".encode())
    return h.hexdigest()[:16]
