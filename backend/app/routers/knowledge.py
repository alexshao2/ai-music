"""Knowledge base endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import KnowledgeChunk
from app.services import knowledge as kb

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/topics", response_model=list[KnowledgeChunk])
def list_topics() -> list[KnowledgeChunk]:
    return kb.list_topics()


@router.get("/search", response_model=list[KnowledgeChunk])
def search(q: str, k: int = 5) -> list[KnowledgeChunk]:
    return kb.search(q, k=k)


@router.get("/doc", response_model=KnowledgeChunk)
def get_doc(path: str) -> KnowledgeChunk:
    chunk = kb.get(path)
    if not chunk:
        raise HTTPException(status_code=404, detail=f"Not found: {path}")
    return chunk


@router.post("/reload")
def reload() -> dict[str, int]:
    return {"loaded": kb.reload()}


@router.post("/rebuild-index")
def rebuild_index() -> dict[str, object]:
    """Re-chunk and re-embed all knowledge files. Requires an embedding key."""
    n_docs = kb.reload()
    n_chunks = kb.rebuild_index()
    return {"docs": n_docs, "chunks": n_chunks, "vector_search": n_chunks > 0}
