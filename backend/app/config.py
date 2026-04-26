"""Application configuration loaded from environment variables."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Generic OpenAI-compatible LLM endpoint (works with OpenAI, Anthropic-via-proxy,
    # any router exposing `/v1/chat/completions`).
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1500
    llm_timeout_sec: float = 180.0

    # Legacy fallbacks (still respected so older .env files keep working).
    openai_api_key: str | None = None
    openai_model: str | None = None
    anthropic_api_key: str | None = None
    anthropic_model: str | None = None

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:3000"

    knowledge_dir: str = "../knowledge"

    # Suno autofill (M4) — drives the user's logged-in Chrome via CDP.
    suno_cdp_url: str = "http://localhost:29229"

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


settings = Settings()
