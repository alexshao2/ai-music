"""FastAPI entrypoint for AI Music backend."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import council, knowledge, studio, suno

app = FastAPI(
    title="AI Music — Hội đồng âm nhạc cấp cao",
    description=(
        "Backend API cho studio sáng tác nhạc dùng hội đồng AI personas + RAG knowledge base "
        "+ Suno bridge."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(council.router)
app.include_router(knowledge.router)
app.include_router(studio.router)
app.include_router(suno.router)


@app.get("/", tags=["meta"])
def root() -> dict[str, object]:
    return {
        "name": "ai-music",
        "version": "0.1.0",
        "has_llm": settings.has_llm,
        "has_embedding": settings.has_embedding,
        "knowledge_dir": str(settings.knowledge_path),
        "endpoints": ["/council", "/knowledge", "/studio", "/suno", "/docs"],
    }


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
