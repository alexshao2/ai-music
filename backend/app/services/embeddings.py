"""Embedding service — separate from the chat LLM.

Embedding models almost always live behind a different endpoint / model id /
quota from chat completions (OpenAI itself routes them through
``/v1/embeddings`` rather than ``/v1/chat/completions``; API routers like
OpenRouter / 9Router expose them as separate entries with their own
permissions). We therefore read embedding config independently from the chat
LLM config, with graceful fallback to the ``LLM_*`` vars for backwards
compatibility.

When no embedding-capable key/base-url is configured the module exports
``available() == False`` and all public functions raise
``EmbeddingUnavailableError``. Callers should check ``available()`` before
calling and fall back to keyword search.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from openai import OpenAI

from app.config import settings

log = logging.getLogger(__name__)


class EmbeddingUnavailableError(RuntimeError):
    """No embedding endpoint/key configured."""


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    if not settings.has_embedding:
        raise EmbeddingUnavailableError("No API key configured for embeddings.")
    return OpenAI(
        api_key=settings.effective_embedding_api_key,
        base_url=settings.effective_embedding_base_url,
        timeout=30.0,
    )


def available() -> bool:
    """Return True if an embedding-capable endpoint is configured."""
    return settings.has_embedding


def _extra_kwargs() -> dict[str, Any]:
    """Only include `dimensions` when the user explicitly configured one.

    Many providers (BGE, e5, Ollama, …) return HTTP 400 when an unsupported
    `dimensions` argument is passed, so default to letting the server choose.
    """
    dim = settings.effective_embedding_dimensions
    return {"dimensions": dim} if dim else {}


def embed_text(text: str) -> list[float]:
    """Embed a single string and return a float vector."""
    client = _client()
    resp = client.embeddings.create(
        model=settings.effective_embedding_model,
        input=text,
        **_extra_kwargs(),
    )
    return resp.data[0].embedding


def embed_batch(texts: list[str], *, batch_size: int = 64) -> list[list[float]]:
    """Embed many strings, respecting the API's per-request batch limit.

    Returns a list of float vectors in the same order as *texts*.
    """
    client = _client()
    all_vecs: list[list[float]] = []
    extra = _extra_kwargs()
    model = settings.effective_embedding_model
    for start in range(0, len(texts), batch_size):
        chunk = texts[start : start + batch_size]
        resp = client.embeddings.create(model=model, input=chunk, **extra)
        sorted_data = sorted(resp.data, key=lambda d: d.index)
        all_vecs.extend(d.embedding for d in sorted_data)
    return all_vecs
