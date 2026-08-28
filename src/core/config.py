import re
from typing import List, Optional
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_db_url(url: str) -> str:
    """
    Normalize database URLs for SQLAlchemy async driver compatibility.
    Converts postgres:// and postgresql:// to postgresql+asyncpg://
    Leaves sqlite+aiosqlite:// and postgresql+asyncpg:// untouched.
    """
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


class Settings(BaseSettings):
    PROJECT_NAME: str = "KYA Agent Registry Microservice"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Database — default is SQLite for local dev; production requires PostgreSQL
    DATABASE_URL: str = "sqlite+aiosqlite:///./kya_dev.db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # JWT — NO hardcoded default.  Must be provided via environment.
    # In development a default is accepted only if ENVIRONMENT != "production".
    JWT_SECRET_KEY: Optional[str] = Field(default=None, description="JWT signing secret — must be set via environment variable")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS — comma-separated list of allowed origins
    # Production requires explicit origins; development defaults to localhost
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Rate limiting (requests per window per IP)
    RATE_LIMIT_AUTH_RPM: int = 10        # /auth/token — 10 requests/minute
    RATE_LIMIT_VERIFY_RPM: int = 30      # /verify-signature — 30 requests/minute
    RATE_LIMIT_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # ------------------------------------------------------------------ #
    # Field-level validators                                               #
    # ------------------------------------------------------------------ #

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        return _normalize_db_url(v)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def validate_cors_origins(cls, v):
        # Accept list (from env as JSON array) or comma-separated string
        if isinstance(v, list):
            return ",".join(v)
        return v

    # ------------------------------------------------------------------ #
    # Cross-field production validation                                    #
    # ------------------------------------------------------------------ #

    @model_validator(mode="after")
    def validate_production_config(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            errors: list[str] = []

            # 1. JWT secret must be explicitly provided
            if not self.JWT_SECRET_KEY:
                errors.append(
                    "JWT_SECRET_KEY must be set via environment variable in production. "
                    "Never use a default or hardcoded secret."
                )

            # 2. Database must be PostgreSQL — reject SQLite
            if self.DATABASE_URL.startswith("sqlite"):
                errors.append(
                    f"DATABASE_URL '{self.DATABASE_URL[:50]}...' uses SQLite which is not "
                    "supported in production. Set a PostgreSQL DATABASE_URL."
                )

            # 3. DATABASE_URL must have been normalised to asyncpg driver
            if not self.DATABASE_URL.startswith("postgresql+asyncpg://"):
                errors.append(
                    "DATABASE_URL must use the 'postgresql+asyncpg://' driver prefix in production."
                )

            # 4. Wildcard CORS in production is not allowed
            if "*" in self.CORS_ORIGINS:
                errors.append(
                    "Wildcard CORS ('*') is not allowed in production. "
                    "Set explicit CORS_ORIGINS."
                )

            if errors:
                formatted = "\n  - ".join([""] + errors)
                raise ValueError(
                    f"[KYA] FATAL: Invalid production configuration:{formatted}"
                )

        # Development: provide a safe test-only default JWT secret if none given
        if self.ENVIRONMENT != "production" and not self.JWT_SECRET_KEY:
            # This value is ONLY used for local development/testing.
            # It MUST NOT appear in production.
            object.__setattr__(
                self,
                "JWT_SECRET_KEY",
                "dev-only-insecure-secret-do-not-use-in-production-ever",
            )

        return self

    def get_cors_origins(self) -> List[str]:
        """Return parsed list of allowed CORS origins."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
