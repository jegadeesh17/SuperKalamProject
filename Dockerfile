# Multi-Stage Production Dockerfile for SuperKalam UPSC Mains Evaluator

# Stage 1: Build virtual environment and install wheels
FROM python:3.11-slim AS builder

WORKDIR /app
# All pinned dependencies ship manylinux wheels for cp311, so no compiler toolchain is needed.
COPY requirements.txt ./
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt && \
    find /opt/venv -depth -type d \( -name tests -o -name test -o -name __pycache__ \) -exec rm -rf {} + && \
    rm -rf /opt/venv/lib/python3.11/site-packages/pip /opt/venv/lib/python3.11/site-packages/pip-* /opt/venv/bin/pip*

# Stage 2: Minimal hardened runtime image
FROM python:3.11-slim AS runner

WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    HOME="/home/appuser"

# Non-root service account
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

COPY --from=builder /opt/venv /opt/venv

COPY --chown=appuser:appgroup agents/ agents/
COPY --chown=appuser:appgroup app/ app/
COPY --chown=appuser:appgroup configs/ configs/
COPY --chown=appuser:appgroup data/ data/
COPY --chown=appuser:appgroup scripts/ scripts/

# Pre-seed SQLite + ChromaDB and pre-cache the ONNX embedding model at build time, so
# every Cloud Run instance boots with data already present (ephemeral filesystem).
# HOME is /home/appuser for both root (build) and appuser (runtime), so Chroma's model
# cache (~/.cache/chroma/onnx_models) written here is the one appuser reads.
RUN mkdir -p db chroma_db reports && \
    python data/ingest.py && \
    chown -R appuser:appgroup db chroma_db reports /home/appuser/.cache

USER appuser

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
