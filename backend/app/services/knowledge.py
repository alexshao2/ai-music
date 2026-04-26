"""Knowledge base loading and (M0) keyword search."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import frontmatter

from app.config import settings
from app.schemas import KnowledgeChunk


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


def reload() -> int:
    all_docs.cache_clear()
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
    """Simple keyword scoring. M1 will swap for embeddings."""
    q = query.lower().strip()
    if not q:
        return []
    terms = [t for t in q.split() if len(t) > 1]
    results: list[tuple[float, _Doc]] = []
    for d in all_docs():
        haystack = (d.title + " " + " ".join(d.tags) + " " + d.body).lower()
        score = 0.0
        for t in terms:
            score += haystack.count(t)
        # Title hits weigh more
        for t in terms:
            score += 3 * d.title.lower().count(t)
        # Tag exact matches
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
