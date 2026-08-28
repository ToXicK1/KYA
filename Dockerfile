# ── Stage 1: dependency builder ─────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: production runtime ─────────────────────────────────────────────
FROM python:3.11-slim

# Install runtime dependencies only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Non-root user (security hardening) ──────────────────────────────────────
# Create a dedicated application user; never run as root in production.
RUN groupadd --gid 10001 kya \
    && useradd --uid 10001 --gid kya --shell /bin/sh --no-create-home kya

COPY --from=builder /install /usr/local
COPY --chown=kya:kya . /app

USER kya

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PORT=8000

# Render dynamically assigns a PORT — we bind to whatever $PORT is set to.
# The EXPOSE directive is documentation-only; the actual port is runtime.
EXPOSE $PORT

# ── Entrypoint ───────────────────────────────────────────────────────────────
# Use shell form so that $PORT environment variable is expanded at runtime.
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --log-level info
