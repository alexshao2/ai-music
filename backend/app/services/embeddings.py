"""Embedding service — OpenAI text-embedding-3-small with dimension control.

When no API key is configured the module exports ``AVAILABLE = False`` and
all public functions raise ``EmbeddingUnavailableError``.  Callers should
check ``AVAILABLE`` before calling and fall back to keyword search.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from openai import OpenAI

from app.config import settings

log = logging.getLogger(__name__)

DIMENSIONS = 1536
MODEL = "text-embedding-3-small"


class EmbeddingUnavailableError(RuntimeError):
    """No embedding key configured."""


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    if not settings.has_llm:
        raise EmbeddingUnavailableError("No API key configured for embeddings.")
    return OpenAI(
        api_key=settings.effective_api_key,
        base_url=settings.effective_base_url,
        timeout=30.0,
    )


def available() -> bool:
    """Return True if an embedding-capable API key is configured."""
    return settings.has_llm


def embed_text(text: str) -> list[float]:
    """Embed a single string and return a float vector."""
    client = _client()
    resp = client.embeddings.create(
        model=MODEL,
        input=text,
        dimensions=DIMENSIONS,
    )
    return resp.data[0].embedding


def embed_batch(texts: list[str], *, batch_size: int = 64) -> list[list[float]]:
    """Embed many strings, respecting the API's per-request batch limit.

    Returns a list of float vectors in the same order as *texts*.
    """
    client = _client()
    all_vecs: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        chunk = texts[start : start + batch_size]
        resp = client.embeddings.create(
            model=MODEL,
            input=chunk,
            dimensions=DIMENSIONS,
        )
        sorted_data = sorted(resp.data, key=lambda d: d.index)
        all_vecs.extend(d.embedding for d in sorted_data)
    return all_vecs
