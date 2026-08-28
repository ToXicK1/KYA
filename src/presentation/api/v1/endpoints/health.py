from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.core.config import settings
from src.core.database import get_db_session

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Liveness probe — lightweight readiness check",
)
async def health_check(session: AsyncSession = Depends(get_db_session)):
    """
    Primary health check — used by Render at /api/v1/health.
    Performs a cheap SELECT 1 to confirm database connectivity.
    """
    try:
        await session.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "service": "agent-registry",
            "version": settings.VERSION,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database probe failed: {str(exc)}",
        )


@router.get(
    "/health/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness probe — all dependency checks",
)
async def readiness_check(session: AsyncSession = Depends(get_db_session)):
    """
    Deep readiness check — verifies all critical dependencies are reachable
    before accepting traffic.  Returns 503 if any dependency is unhealthy.
    """
    checks = {}
    is_ready = True

    # Database connectivity
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception as exc:
        checks["database"] = f"disconnected: {str(exc)}"
        is_ready = False

    if not is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "checks": checks},
        )

    return {
        "status": "ready",
        "checks": checks,
        "service": "agent-registry",
        "version": settings.VERSION,
    }
