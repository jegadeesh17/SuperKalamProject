# Multi-Stage Production Dockerfile for SuperKalam UPSC Mains Evaluator

# Stage 1: Build virtual environment and install wheels
FROM python:3.11-slim AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Stage 2: Minimal hardened runtime image
FROM python:3.11-slim AS runner

WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    HF_HOME="/app/.cache/huggingface" \
    SENTENCE_TRANSFORMERS_HOME="/app/.cache/sentence_transformers"

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Non-root service account
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

COPY --from=builder /opt/venv /opt/venv

COPY --chown=appuser:appgroup agents/ agents/
COPY --chown=appuser:appgroup app/ app/
COPY --chown=appuser:appgroup configs/ configs/
COPY --chown=appuser:appgroup data/ data/
COPY --chown=appuser:appgroup scripts/ scripts/

# Pre-seed SQLite + ChromaDB and pre-cache the embedding model at build time, so
# every Cloud Run instance boots with data already present (ephemeral filesystem).
RUN mkdir -p db chroma_db reports "$HF_HOME" "$SENTENCE_TRANSFORMERS_HOME" && \
    python data/ingest.py && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f "http://localhost:${PORT:-8080}/health" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
