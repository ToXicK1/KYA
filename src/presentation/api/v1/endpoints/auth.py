from fastapi import APIRouter, HTTPException, Request, status
from src.presentation.api.schemas.auth_schemas import Token, LoginRequest
from src.core.security import create_access_token
from src.core.config import settings
from src.core.middleware.rate_limit_middleware import enforce_rate_limit
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/token",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Obtain JWT Bearer Authentication Token",
    responses={
        401: {"description": "Invalid credentials"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def login_for_access_token(request: Request, payload: LoginRequest):
    # Rate-limit brute-force attacks on the token endpoint
    enforce_rate_limit(
        request,
        route_key="auth-token",
        limit=settings.RATE_LIMIT_AUTH_RPM,
        window_seconds=60,
    )

    # In enterprise production, authenticate against LDAP/OIDC/IDP.
    # For demonstration/testing, validate non-empty credentials.
    if not payload.username or not payload.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    expires_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    access_token = create_access_token(
        data={
            "sub": payload.username,
            "org": payload.organization,
            "roles": ["kya_admin", "agent_registrar"],
        },
        expires_delta=timedelta(minutes=expires_minutes),
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_minutes * 60,
    )
