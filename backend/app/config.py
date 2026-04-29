"""Application configuration loaded from environment variables."""
from __future__ import annotations

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Generic OpenAI-compatible LLM endpoint (works with OpenAI, Anthropic-via-proxy,
    # any router exposing `/v1/chat/completions`).
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.7
    # Upper bound on completion tokens per persona turn. Lyricist + Arranger
    # schemas emit a single JSON blob that routinely exceeds 1500 tokens (full
    # Vietnamese lyrics with markers, prosody notes, per-section textures,
    # drum/bass maps, etc.). A low limit silently truncates JSON mid-string,
    # which fails `_extract_json` and collapses that persona to the stub —
    # leaving the user with placeholder lyrics ("[chờ Lyricist tinh chỉnh]").
    # 4000 fits current schemas comfortably; bump via LLM_MAX_TOKENS if needed.
    llm_max_tokens: int = 4000
    # Total per-request budget enforced two ways:
    # 1. As the fallback ``timeout`` for any httpx phase not explicitly
    #    overridden below (currently ``write`` / ``pool``).
    # 2. As an explicit wall-clock cap on the streaming loop in
    #    :func:`app.services.llm.chat` — a model dribbling one chunk
    #    just under ``llm_read_timeout_sec`` would otherwise stream
    #    forever, so we raise once total elapsed exceeds this value.
    llm_timeout_sec: float = 180.0
    # TCP connect timeout. Should fail fast — if the LLM endpoint isn't
    # reachable we want the persona retry loop to substitute a stub,
    # not wait 3 minutes per attempt.
    llm_connect_timeout_sec: float = 10.0
    # Read timeout BETWEEN STREAM CHUNKS. The OpenAI Chat Completions
    # streaming protocol pushes a chunk every few seconds while the
    # model is generating; if more than this many seconds pass without
    # a chunk we treat the connection as silently dead and raise.
    # 60s is generous for a healthy model and aggressive enough that a
    # network drop mid-compose surfaces as a persona retry within ~1
    # minute instead of hanging for the full ``llm_timeout_sec``.
    llm_read_timeout_sec: float = 60.0

    # Embedding endpoint — separate from chat/LLM because many providers (OpenAI
    # compat routers, vLLM, Ollama, ...) expose embedding models under a
    # different route / API key / quota than chat models. All four fields are
    # optional; each independently falls back to the `llm_*` equivalent when
    # unset, so users who already had a single LLM_* config keep working.
    embedding_base_url: str | None = None
    embedding_api_key: str | None = None
    embedding_model: str | None = None
    # Leave unset (None or 0) to let the provider pick its native dimension.
    # OpenAI text-embedding-3-* honour a requested output dimension; others
    # (e.g. BGE, e5) ignore this and always return their native size.
    embedding_dimensions: int | None = None

    @field_validator("embedding_dimensions", mode="before")
    @classmethod
    def _blank_dim_is_none(cls, v: object) -> object:
        # docker-compose expands `${EMBEDDING_DIMENSIONS:-}` to an empty string
        # when the user hasn't set it, which pydantic rejects for `int | None`.
        if isinstance(v, str) and not v.strip():
            return None
        return v

    # Legacy fallbacks (still respected so older .env files keep working).
    openai_api_key: str | None = None
    openai_model: str | None = None
    anthropic_api_key: str | None = None
    anthropic_model: str | None = None

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:3000"

    knowledge_dir: str = "../knowledge"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def knowledge_path(self) -> Path:
        p = Path(self.knowledge_dir)
        if not p.is_absolute():
            p = (Path(__file__).resolve().parent.parent / p).resolve()
        return p

    @property
    def effective_api_key(self) -> str | None:
        return self.llm_api_key or self.openai_api_key

    @property
    def effective_base_url(self) -> str | None:
        # Default to OpenAI's official endpoint when only OPENAI_API_KEY is set.
        if self.llm_base_url:
            return self.llm_base_url
        if self.openai_api_key:
            return "https://api.openai.com/v1"
        return None

    @property
    def effective_model(self) -> str:
        return self.llm_model or self.openai_model or "gpt-4o-mini"

    @property
    def has_llm(self) -> bool:
        return bool(self.effective_api_key and self.effective_base_url)

    # --- Embedding resolution (each field falls back to its LLM counterpart) ---

    @property
    def effective_embedding_api_key(self) -> str | None:
        return self.embedding_api_key or self.effective_api_key

    @property
    def effective_embedding_base_url(self) -> str | None:
        return self.embedding_base_url or self.effective_base_url

    @property
    def effective_embedding_model(self) -> str:
        # Chat model is useless for the /embeddings endpoint, so don't fall back
        # to `llm_model` here — pick a sane OpenAI-compatible default instead.
        return self.embedding_model or "text-embedding-3-small"

    @property
    def effective_embedding_dimensions(self) -> int | None:
        dim = self.embedding_dimensions
        return dim if dim and dim > 0 else None

    @property
    def has_embedding(self) -> bool:
        return bool(self.effective_embedding_api_key and self.effective_embedding_base_url)


settings = Settings()
