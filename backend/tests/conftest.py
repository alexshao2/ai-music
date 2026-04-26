"""Test config: force the deterministic council path so smoke tests stay offline.

We import ``app.config`` and then null out every credential the council service
would otherwise use. ``Settings()`` is a Pydantic model with model_config
``env_file=".env"`` — even if the dev ``.env`` has real keys, this conftest
runs first and wipes them.
"""
from __future__ import annotations

from app.config import settings as _settings

_settings.llm_api_key = None
_settings.llm_base_url = None
_settings.openai_api_key = None
_settings.anthropic_api_key = None

assert not _settings.has_llm, "Tests must run without an LLM key configured."
