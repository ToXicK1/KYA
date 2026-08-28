from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html

from src.core.config import settings
from src.core.database import engine, Base
from src.core.logging import logger
from src.core.middleware.exception_middleware import ExceptionHandlingMiddleware
from src.core.middleware.security_headers_middleware import SecurityHeadersMiddleware
from src.presentation.api.v1.router import api_router

# Ensure ORM models are registered with SQLAlchemy metadata
from src.infrastructure.db.models.agent_model import AgentModel, PublicKeyModel  # noqa: F401


# ------------------------------------------------------------------ #
# Lifespan                                                             #
# ------------------------------------------------------------------ #

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifecycle — startup → yield → shutdown."""
    logger.info(
        f"Starting {settings.PROJECT_NAME} v{settings.VERSION} "
        f"in [{settings.ENVIRONMENT}] mode."
    )

    if settings.ENVIRONMENT != "production":
        # In development / test we auto-create tables for zero-friction local runs.
        # Production uses Alembic migrations via scripts/pre_deploy.sh.
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Dev/test: database tables ensured via create_all.")

    logger.info(f"{settings.PROJECT_NAME} startup complete.")
    yield

    # ── Shutdown ──
    logger.info(f"Shutting down {settings.PROJECT_NAME}.")
    await engine.dispose()
    logger.info("SQLAlchemy engine disposed.")


# ------------------------------------------------------------------ #
# FastAPI application                                                  #
# ------------------------------------------------------------------ #

_is_production = settings.ENVIRONMENT == "production"

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    # Disable interactive docs in production (security hardening)
    openapi_url=None if _is_production else f"{settings.API_V1_STR}/openapi.json",
    docs_url=None,
    redoc_url=None,
    description=(
        "# Know Your Agent (KYA) — Enterprise Agent Registry Microservice\n\n"
        "Production-grade Agent Registry providing cryptographic identity management, "
        "manifest storage, zero-trust public key verifications, JWT security, and agent governance."
    ),
)

# ------------------------------------------------------------------ #
# Middleware — order matters (outermost = last added)                  #
# ------------------------------------------------------------------ #

# 1. Security headers (outermost — applied to every response)
app.add_middleware(SecurityHeadersMiddleware)

# 2. Domain exception handler
app.add_middleware(ExceptionHandlingMiddleware)

# 3. CORS — driven entirely by environment variable
_cors_origins = settings.get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,           # credentials=True + wildcard is a security risk
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# ------------------------------------------------------------------ #
# Routers                                                              #
# ------------------------------------------------------------------ #

app.include_router(api_router, prefix=settings.API_V1_STR)


# ------------------------------------------------------------------ #
# Root-level health check (Render default probe path)                 #
# ------------------------------------------------------------------ #

@app.get("/health", include_in_schema=False, tags=["Health"])
async def root_health():
    """Lightweight liveness probe — no external dependencies checked."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


# ------------------------------------------------------------------ #
# Interactive API documentation — development only                    #
# ------------------------------------------------------------------ #

if not _is_production:
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=f"{settings.API_V1_STR}/openapi.json",
            title=f"{settings.PROJECT_NAME} - Swagger UI",
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.11.0/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.11.0/swagger-ui.css",
        )

    @app.get("/redoc", include_in_schema=False)
    async def custom_redoc_html():
        return get_redoc_html(
            openapi_url=f"{settings.API_V1_STR}/openapi.json",
            title=f"{settings.PROJECT_NAME} - ReDoc",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.1.5/bundles/redoc.standalone.js",
        )
