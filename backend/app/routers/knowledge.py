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
