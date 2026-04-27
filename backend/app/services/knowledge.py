"""Knowledge base: markdown loading, heading-level chunking, and hybrid search.

M0 used whole-document keyword matching.  M1 upgrades to:
  1. **Chunking** — each markdown file is split by ``##`` headings into
     self-contained passages so retrieval is more precise.
  2. **Vector search** — when an OpenAI-compatible embedding key is
     configured, chunks are embedded (text-embedding-3-small) and searched
     via cosine similarity.  The index is persisted to disk (``.npz``) so
     re-embedding only happens when the corpus changes.
  3. **Keyword fallback** — when no key is available (CI, local dev without
     key), the original keyword scorer is used.

Council integration is unchanged: ``_retrieve_for()`` calls ``search()``
and gets better results automatically.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import frontmatter

from app.config import settings
from app.schemas import KnowledgeChunk
from app.services.vector_store import Chunk, VectorStore, corpus_hash

log = logging.getLogger(__name__)

# Module-level singleton — built lazily on first vector search.
_store: VectorStore | None = None
_store_hash: str | None = None


# ---------------------------------------------------------------------------
# Document loading
# ---------------------------------------------------------------------------

@dataclass
class _Doc:
    path: str
    title: str
    tags: tuple[str, ...]
    level: str | None
    body: str


def _load_all() -> list[_Doc]:
    root = settings.knowledge_path
    if not root.exists():
        return []
    docs: list[_Doc] = []
    for md in sorted(root.rglob("*.md")):
        post = frontmatter.load(md)
        meta = post.metadata or {}
        title = str(meta.get("title") or md.stem.replace("-", " ").title())
        tags = tuple(str(t) for t in (meta.get("tags") or []))
        level = meta.get("level")
        rel = md.relative_to(root).as_posix()
        docs.append(
            _Doc(path=rel, title=title, tags=tags, level=str(level) if level else None, body=post.content)
        )
    return docs


@lru_cache(maxsize=1)
def all_docs() -> list[_Doc]:
    return _load_all()


# ---------------------------------------------------------------------------
# Chunking by heading
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)


def chunk_doc(doc: _Doc) -> list[Chunk]:
    """Split a document into chunks by ## / ### headings.

    Each chunk inherits the parent doc's metadata.  Short chunks (< 40 chars)
    are merged into their predecessor to avoid tiny fragments.
    """
    body = doc.body.strip()
    if not body:
        return []

    splits: list[tuple[int, str]] = []  # (char_offset, heading_text)
    for m in _HEADING_RE.finditer(body):
        splits.append((m.start(), m.group(2).strip()))

    if not splits:
        return [
            Chunk(
                doc_path=doc.path,
                doc_title=doc.title,
                doc_tags=doc.tags,
                doc_level=doc.level,
                heading=doc.title,
                body=body,
                char_offset=0,
            )
        ]

    chunks: list[Chunk] = []

    # Text before the first heading
    if splits[0][0] > 0:
        preamble = body[: splits[0][0]].strip()
        if len(preamble) >= 40:
            chunks.append(
                Chunk(
                    doc_path=doc.path,
                    doc_title=doc.title,
                    doc_tags=doc.tags,
                    doc_level=doc.level,
                    heading=doc.title,
                    body=preamble,
                    char_offset=0,
                )
            )

    for i, (offset, heading) in enumerate(splits):
        end = splits[i + 1][0] if i + 1 < len(splits) else len(body)
        section_body = body[offset:end].strip()
        # Remove the heading line itself from the body
        first_newline = section_body.find("\n")
        if first_newline > 0:
            section_body = section_body[first_newline:].strip()
        else:
            section_body = ""

        if len(section_body) < 40 and chunks:
            # Merge tiny chunk into previous
            chunks[-1].body += f"\n\n### {heading}\n{section_body}"
            continue

        if not section_body:
            continue

        chunks.append(
            Chunk(
                doc_path=doc.path,
                doc_title=doc.title,
                doc_tags=doc.tags,
                doc_level=doc.level,
                heading=heading,
                body=section_body,
                char_offset=offset,
            )
        )

    # If no chunks were created (e.g. only tiny headings), return whole doc
    if not chunks:
        chunks.append(
            Chunk(
                doc_path=doc.path,
                doc_title=doc.title,
                doc_tags=doc.tags,
                doc_level=doc.level,
                heading=doc.title,
                body=body,
                char_offset=0,
            )
        )

    return chunks


def all_chunks() -> list[Chunk]:
    """Chunk every loaded document."""
    out: list[Chunk] = []
    for doc in all_docs():
        out.extend(chunk_doc(doc))
    return out


# ---------------------------------------------------------------------------
# Vector index management
# ---------------------------------------------------------------------------

def _index_path() -> Path:
    return settings.knowledge_path.parent / "backend" / "app" / "data" / "index" / "knowledge"


def _ensure_index() -> VectorStore | None:
    """Build or load the vector index if embeddings are available."""
    global _store, _store_hash  # noqa: PLW0603

    from app.services import embeddings as emb_svc

    if not emb_svc.available():
        return None

    chunks = all_chunks()
    current_hash = corpus_hash(chunks)

    # Already built and up-to-date
    if _store is not None and _store_hash == current_hash:
        return _store

    # Try loading from disk
    idx_path = _index_path()
    loaded = VectorStore.load(idx_path)
    if loaded is not None and loaded.size == len(chunks):
        _store = loaded
        _store_hash = current_hash
        log.info("Loaded vector index from disk (%d chunks)", loaded.size)
        return _store

    # Build from scratch
    log.info("Building vector index for %d chunks...", len(chunks))
    texts = [c.text_for_embedding for c in chunks]
    try:
        vectors = emb_svc.embed_batch(texts)
    except Exception:
        log.exception("Embedding failed — falling back to keyword search")
        return None

    store = VectorStore(chunks=chunks)
    store.set_embeddings(vectors)
    store.save(idx_path)
    _store = store
    _store_hash = current_hash
    log.info("Vector index built and saved (%d chunks)", len(chunks))
    return _store


def rebuild_index() -> int:
    """Force rebuild the vector index. Returns chunk count."""
    global _store, _store_hash  # noqa: PLW0603
    _store = None
    _store_hash = None
    store = _ensure_index()
    return store.size if store else 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def reload() -> int:
    """Reload docs from disk and invalidate the vector index."""
    global _store, _store_hash  # noqa: PLW0603
    all_docs.cache_clear()
    _store = None
    _store_hash = None
    return len(all_docs())


def list_topics() -> list[KnowledgeChunk]:
    return [
        KnowledgeChunk(
            path=d.path,
            title=d.title,
            tags=list(d.tags),
            level=d.level,
            excerpt=d.body[:240].strip(),
            score=0.0,
        )
        for d in all_docs()
    ]


def search(query: str, k: int = 5) -> list[KnowledgeChunk]:
    """Hybrid search: try vector search first, fall back to keyword.

    Vector search returns *chunk-level* results (more precise). Keyword
    search returns *document-level* results (same as M0).
    """
    q = query.strip()
    if not q:
        return []

    # Try vector search
    store = _ensure_index()
    if store is not None:
        return _vector_search(store, q, k)

    # Keyword fallback
    return _keyword_search(q, k)


def _vector_search(store: VectorStore, query: str, k: int) -> list[KnowledgeChunk]:
    """Embed query and search the vector index."""
    from app.services import embeddings as emb_svc

    try:
        query_vec = emb_svc.embed_text(query)
    except Exception:
        log.warning("Query embedding failed — falling back to keyword search")
        return _keyword_search(query, k)

    results = store.search(query_vec, k=k)
    out: list[KnowledgeChunk] = []
    for score, idx in results:
        chunk = store.chunks[idx]
        out.append(
            KnowledgeChunk(
                path=chunk.doc_path,
                title=f"{chunk.doc_title} › {chunk.heading}" if chunk.heading != chunk.doc_title else chunk.doc_title,
                tags=list(chunk.doc_tags),
                level=chunk.doc_level,
                excerpt=chunk.body[:400].strip(),
                score=round(score, 4),
            )
        )
    return out


def _keyword_search(query: str, k: int) -> list[KnowledgeChunk]:
    """Original M0 keyword scoring — document-level."""
    q = query.lower()
    terms = [t for t in q.split() if len(t) > 1]
    results: list[tuple[float, _Doc]] = []
    for d in all_docs():
        haystack = (d.title + " " + " ".join(d.tags) + " " + d.body).lower()
        score = 0.0
        for t in terms:
            score += haystack.count(t)
        for t in terms:
            score += 3 * d.title.lower().count(t)
        for t in terms:
            if t in d.tags:
                score += 5
        if score > 0:
            results.append((score, d))
    results.sort(key=lambda x: x[0], reverse=True)
    out: list[KnowledgeChunk] = []
    for score, d in results[:k]:
        out.append(
            KnowledgeChunk(
                path=d.path,
                title=d.title,
                tags=list(d.tags),
                level=d.level,
                excerpt=d.body[:400].strip(),
                score=round(score, 2),
            )
        )
    return out


def get(path: str) -> KnowledgeChunk | None:
    for d in all_docs():
        if d.path == path:
            return KnowledgeChunk(
                path=d.path,
                title=d.title,
                tags=list(d.tags),
                level=d.level,
                excerpt=d.body,
                score=0.0,
            )
    return None
