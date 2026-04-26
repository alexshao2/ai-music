"""Application configuration loaded from environment variables."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-3-5-sonnet-latest"

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
    def has_llm(self) -> bool:
        return bool(self.openai_api_key or self.anthropic_api_key)


settings = Settings()
