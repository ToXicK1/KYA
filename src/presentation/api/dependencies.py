from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.core.database import get_db_session
from src.core.security import decode_access_token, SecurityException
from src.presentation.api.schemas.auth_schemas import TokenData
from src.domain.interfaces.repositories import AgentRepositoryInterface
from src.domain.interfaces.crypto_verifier import CryptoVerifierInterface
from src.infrastructure.db.repositories.postgres_agent_repository import PostgresAgentRepository
from src.infrastructure.crypto.key_verifier_service import PyCAKeyVerifierService
from src.use_cases.register_agent import RegisterAgentUseCase
from src.use_cases.get_agent import GetAgentUseCase
from src.use_cases.verify_agent_key import VerifyAgentSignatureUseCase
from src.use_cases.list_agents import ListAgentsUseCase
from src.use_cases.update_agent_status import UpdateAgentStatusUseCase

security_scheme = HTTPBearer(auto_error=False)


# ------------------------------------------------------------------ #
# Authentication                                                       #
# ------------------------------------------------------------------ #

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> TokenData:
    """
    Validate Bearer JWT and return parsed token claims.
    Raises 401 if the token is missing, expired, or invalid.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Bearer token header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
        username: str = payload.get("sub", "")
        organization: str = payload.get("org", "")
        roles: list = payload.get("roles", [])
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
            )
        return TokenData(username=username, organization=organization, roles=roles)
    except SecurityException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )


# ------------------------------------------------------------------ #
# Authorization                                                        #
# ------------------------------------------------------------------ #

def require_roles(allowed_roles: List[str]):
    """
    Factory that returns a FastAPI dependency enforcing role-based access.

    Usage::

        @router.post("/agents", dependencies=[Depends(require_roles(["kya_admin"]))])
        async def register_agent(...): ...

    Raises:
        401 — if no valid JWT is present
        403 — if JWT is valid but user lacks the required role
    """
    def _check_roles(token: TokenData = Depends(get_current_user)) -> TokenData:
        if not any(role in token.roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Insufficient permissions. Required role(s): {allowed_roles}. "
                    f"Your roles: {token.roles}."
                ),
            )
        return token

    return _check_roles


# ------------------------------------------------------------------ #
# Infrastructure / Use-case factories                                  #
# ------------------------------------------------------------------ #

def get_crypto_verifier() -> CryptoVerifierInterface:
    return PyCAKeyVerifierService()


def get_agent_repository(
    session: AsyncSession = Depends(get_db_session),
) -> AgentRepositoryInterface:
    return PostgresAgentRepository(session)


def get_register_agent_use_case(
    repo: AgentRepositoryInterface = Depends(get_agent_repository),
    crypto: CryptoVerifierInterface = Depends(get_crypto_verifier),
) -> RegisterAgentUseCase:
    return RegisterAgentUseCase(repository=repo, crypto_verifier=crypto)


def get_agent_use_case(
    repo: AgentRepositoryInterface = Depends(get_agent_repository),
) -> GetAgentUseCase:
    return GetAgentUseCase(repository=repo)


def get_verify_signature_use_case(
    repo: AgentRepositoryInterface = Depends(get_agent_repository),
    crypto: CryptoVerifierInterface = Depends(get_crypto_verifier),
) -> VerifyAgentSignatureUseCase:
    return VerifyAgentSignatureUseCase(repository=repo, crypto_verifier=crypto)


def get_list_agents_use_case(
    repo: AgentRepositoryInterface = Depends(get_agent_repository),
) -> ListAgentsUseCase:
    return ListAgentsUseCase(repository=repo)


def get_update_status_use_case(
    repo: AgentRepositoryInterface = Depends(get_agent_repository),
) -> UpdateAgentStatusUseCase:
    return UpdateAgentStatusUseCase(repository=repo)
