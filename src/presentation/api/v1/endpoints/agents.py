import base64
from fastapi import APIRouter, Depends, status, HTTPException, Query, Request
from typing import List, Optional

from src.presentation.api.schemas.agent_schemas import (
    AgentRegisterRequest,
    AgentResponse,
    AgentStatusUpdateRequest,
    SignatureVerificationRequest,
    SignatureVerificationResponse,
    AgentManifestSchema,
    PublicKeyResponse,
)
from src.presentation.api.schemas.error_schemas import ErrorResponse
from src.presentation.api.dependencies import (
    get_register_agent_use_case,
    get_agent_use_case,
    get_verify_signature_use_case,
    get_list_agents_use_case,
    get_update_status_use_case,
    require_roles,
)
from src.use_cases.register_agent import RegisterAgentUseCase, RegisterAgentDTO, PublicKeyDTO
from src.use_cases.get_agent import GetAgentUseCase
from src.use_cases.verify_agent_key import VerifyAgentSignatureUseCase, SignatureVerificationDTO
from src.use_cases.list_agents import ListAgentsUseCase
from src.use_cases.update_agent_status import UpdateAgentStatusUseCase
from src.domain.value_objects.agent_status import AgentStatus
from src.domain.entities.agent import Agent
from src.core.config import settings
from src.core.middleware.rate_limit_middleware import enforce_rate_limit

router = APIRouter(prefix="/agents", tags=["Agents"])


def _to_agent_response(agent: Agent) -> AgentResponse:
    return AgentResponse(
        id=agent.id.value,
        status=agent.status,
        owner_organization=agent.owner_organization,
        manifest=AgentManifestSchema(
            name=agent.manifest.name,
            version=agent.manifest.version,
            description=agent.manifest.description,
            owner_organization=agent.manifest.owner_organization,
            capabilities=agent.manifest.capabilities,
            endpoints=agent.manifest.endpoints,
            operational_bounds=agent.manifest.operational_bounds,
        ),
        manifest_hash=agent.manifest.compute_hash(),
        public_keys=[
            PublicKeyResponse(
                key_id=pk.key_id,
                algorithm=pk.algorithm,
                pem_content=pk.pem_content,
                is_active=pk.is_active,
                created_at=pk.created_at,
                expires_at=pk.expires_at,
            )
            for pk in agent.public_keys
        ],
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


# ------------------------------------------------------------------ #
# POST /agents — PROTECTED: kya_admin role required                   #
# ------------------------------------------------------------------ #

@router.post(
    "",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new AI Agent",
    dependencies=[Depends(require_roles(["kya_admin"]))],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid key or private key rejection"},
        401: {"model": ErrorResponse, "description": "Missing or invalid authentication token"},
        403: {"model": ErrorResponse, "description": "Insufficient role permissions"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def register_agent(
    payload: AgentRegisterRequest,
    use_case: RegisterAgentUseCase = Depends(get_register_agent_use_case),
):
    dto = RegisterAgentDTO(
        name=payload.name,
        version=payload.version,
        description=payload.description,
        owner_organization=payload.owner_organization,
        capabilities=payload.capabilities,
        endpoints=payload.endpoints,
        operational_bounds=payload.operational_bounds,
        public_keys=[
            PublicKeyDTO(
                algorithm=pk.algorithm,
                pem_content=pk.pem_content,
                expires_at=pk.expires_at,
            )
            for pk in payload.public_keys
        ],
    )
    agent = await use_case.execute(dto)
    return _to_agent_response(agent)


# ------------------------------------------------------------------ #
# GET /agents/{agent_id} — public read                                #
# ------------------------------------------------------------------ #

@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Agent identity & manifest by ID",
    responses={404: {"model": ErrorResponse, "description": "Agent not found"}},
)
async def get_agent(
    agent_id: str,
    use_case: GetAgentUseCase = Depends(get_agent_use_case),
):
    agent = await use_case.execute(agent_id)
    return _to_agent_response(agent)


# ------------------------------------------------------------------ #
# GET /agents — public read with pagination                           #
# ------------------------------------------------------------------ #

@router.get(
    "",
    response_model=List[AgentResponse],
    status_code=status.HTTP_200_OK,
    summary="List agents with pagination and filtering",
)
async def list_agents(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: Optional[AgentStatus] = Query(None, alias="status"),
    owner_organization: Optional[str] = Query(None),
    use_case: ListAgentsUseCase = Depends(get_list_agents_use_case),
):
    agents = await use_case.execute(
        limit=limit,
        offset=offset,
        status=status_filter,
        owner_organization=owner_organization,
    )
    return [_to_agent_response(a) for a in agents]


# ------------------------------------------------------------------ #
# PATCH /agents/{agent_id}/status — PROTECTED: kya_admin role        #
# ------------------------------------------------------------------ #

@router.patch(
    "/{agent_id}/status",
    response_model=AgentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Agent status (Suspend/Revoke/Activate)",
    dependencies=[Depends(require_roles(["kya_admin"]))],
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse, "description": "Missing or invalid authentication token"},
        403: {"model": ErrorResponse, "description": "Insufficient role permissions"},
        404: {"model": ErrorResponse},
    },
)
async def update_agent_status(
    agent_id: str,
    payload: AgentStatusUpdateRequest,
    use_case: UpdateAgentStatusUseCase = Depends(get_update_status_use_case),
):
    agent = await use_case.execute(agent_id, payload.status)
    return _to_agent_response(agent)


# ------------------------------------------------------------------ #
# POST /agents/verify-signature — rate limited                        #
# ------------------------------------------------------------------ #

@router.post(
    "/verify-signature",
    response_model=SignatureVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify cryptographic signature against registered agent key",
    responses={429: {"description": "Rate limit exceeded"}},
)
async def verify_signature(
    request: Request,
    payload: SignatureVerificationRequest,
    use_case: VerifyAgentSignatureUseCase = Depends(get_verify_signature_use_case),
):
    # Rate limit: protect CPU-heavy cryptographic verification
    enforce_rate_limit(
        request,
        route_key="verify-signature",
        limit=settings.RATE_LIMIT_VERIFY_RPM,
        window_seconds=60,
    )

    message_bytes = base64.b64decode(payload.message_base64)
    signature_bytes = base64.b64decode(payload.signature_base64)

    dto = SignatureVerificationDTO(
        key_id=payload.key_id,
        message=message_bytes,
        signature=signature_bytes,
    )
    result = await use_case.execute(dto)
    return SignatureVerificationResponse(
        is_valid=result.is_valid,
        agent_id=result.agent_id,
        owner_organization=result.owner_organization,
        key_algorithm=result.key_algorithm,
    )
