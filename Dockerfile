# =============================================================================
# GitSummarize Backend — Multi-stage Dockerfile
# =============================================================================

# --------------- Stage 1: base dependencies -----------------------------------
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --------------- Stage 2: install Python deps ---------------------------------
FROM base AS dependencies

# Tell poetry's pip subprocess to find CPU-only PyTorch wheels
ENV PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu

COPY pyproject.toml poetry.lock* ./
RUN pip install poetry==1.8.3 && \
    poetry config virtualenvs.create false && \
    poetry lock && \
    poetry install --no-root --without dev

# --------------- Stage 3: production image ------------------------------------
FROM dependencies AS production

COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini ./

ENV HF_HOME=/app/.cache

# Pre-download sentence-transformers model at build time (stored in /app/.cache)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# --------------- Stage 4: development image -----------------------------------
FROM dependencies AS development

RUN poetry install --no-root --with dev

COPY . .

USER root
