# syntax=docker/dockerfile:1.7

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps: curl for healthcheck, build-essential only if a wheel is missing.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (better layer caching).
COPY backend/pyproject.toml /app/backend/pyproject.toml
RUN pip install --upgrade pip \
    && pip install /app/backend

# Copy backend source and the knowledge directory (read at runtime via KNOWLEDGE_DIR).
COPY backend /app/backend
COPY knowledge /app/knowledge

ENV KNOWLEDGE_DIR=/app/knowledge \
    HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app/backend

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000}"]
