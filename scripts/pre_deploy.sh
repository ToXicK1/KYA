#!/usr/bin/env bash
# =============================================================================
# KYA Agent Registry — Render Pre-Deploy Script
# =============================================================================
# This script runs BEFORE the container starts on Render (Pre-Deploy Command).
# It executes Alembic database migrations to ensure the schema is always up
# to date before the application begins serving traffic.
#
# Usage on Render:
#   Pre-Deploy Command: bash scripts/pre_deploy.sh
#
# Local usage:
#   DATABASE_URL=postgresql+asyncpg://... bash scripts/pre_deploy.sh
# =============================================================================

set -euo pipefail

echo "[pre-deploy] Starting KYA Agent Registry pre-deploy checks..."
echo "[pre-deploy] Environment: ${ENVIRONMENT:-development}"
echo "[pre-deploy] Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# ── Validate required production environment variables ─────────────────────
if [ "${ENVIRONMENT:-}" = "production" ]; then
  if [ -z "${DATABASE_URL:-}" ]; then
    echo "[pre-deploy] FATAL: DATABASE_URL is not set. Aborting deployment." >&2
    exit 1
  fi
  if [ -z "${JWT_SECRET_KEY:-}" ]; then
    echo "[pre-deploy] FATAL: JWT_SECRET_KEY is not set. Aborting deployment." >&2
    exit 1
  fi
  echo "[pre-deploy] Production environment variables validated."
fi

# ── Run Alembic migrations ─────────────────────────────────────────────────
echo "[pre-deploy] Running database migrations via Alembic..."
python -m alembic upgrade head
echo "[pre-deploy] Database migrations complete."

echo "[pre-deploy] Pre-deploy script finished successfully."
