"""Pydantic schemas shared across routers."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Brief(BaseModel):
    """User brief for a new composition."""

    mood: str = Field(..., description="Cảm xúc chủ đạo, vd: 'hoài niệm, chậm rãi'")
    genre: str = Field(..., description="Thể loại, vd: 'indie folk', 'V-pop ballad'")
    language: str = Field("vi", description="Ngôn ngữ lời, vd: 'vi', 'en'")
    duration_sec: int = Field(180, ge=30, le=600)
    references: list[str] = Field(default_factory=list, description="Bài tham chiếu")
    notes: str | None = Field(None, description="Ghi chú thêm")


class CouncilTurn(BaseModel):
    persona: str
    role: str
    message: str


class Section(BaseModel):
    section: Literal["intro", "verse", "pre_chorus", "chorus", "bridge", "outro", "instrumental"]
    bars: int = Field(..., ge=1, le=64)
    chords: list[str] = Field(default_factory=list)
    notes: str | None = None


class SongDraft(BaseModel):
    id: str
    title: str
    brief: Brief
    key: str
    tempo_bpm: int
    structure: list[Section]
    lyrics: dict[str, str] = Field(default_factory=dict)
    arrangement: dict[str, object] = Field(default_factory=dict)
    production: dict[str, object] = Field(default_factory=dict)
    council_log: list[CouncilTurn] = Field(default_factory=list)
    suno_prompt: dict[str, str] | None = None


class KnowledgeChunk(BaseModel):
    path: str
    title: str
    tags: list[str] = Field(default_factory=list)
    level: str | None = None
    excerpt: str
    score: float = 0.0


class SunoPrompt(BaseModel):
    style: str = Field(..., description="≤200 ký tự, mô tả style cho Suno")
    lyrics: str = Field(..., description="Lyrics định dạng [Verse]/[Chorus]/...")
    title: str = Field(...)
