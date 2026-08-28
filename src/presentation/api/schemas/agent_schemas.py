from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.domain.value_objects.agent_status import AgentStatus
from src.domain.value_objects.key_algorithm import KeyAlgorithm


class PublicKeyRegisterRequest(BaseModel):
    algorithm: KeyAlgorithm = Field(..., description="Cryptographic algorithm for the public key")
    pem_content: str = Field(
        ...,
        description="PEM formatted public key string. PRIVATE KEYS FORBIDDEN.",
        json_schema_extra={"example": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"}
    )
    expires_at: Optional[datetime] = None


class PublicKeyResponse(BaseModel):
    key_id: str = Field(..., description="SHA-256 fingerprint hash of the public key")
    algorithm: KeyAlgorithm
    pem_content: str
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None


class AgentManifestSchema(BaseModel):
    name: str = Field(..., json_schema_extra={"example": "Autonomous Settlement Bot"})
    version: str = Field(..., json_schema_extra={"example": "1.2.0"})
    description: str = Field(..., json_schema_extra={"example": "Agent for cross-border ledger reconciliation"})
    owner_organization: str = Field(..., json_schema_extra={"example": "org_google_cloud"})
    capabilities: List[str] = Field(
        default_factory=list,
        json_schema_extra={"example": ["ledger_read", "payment_settle"]}
    )
    endpoints: List[str] = Field(
        default_factory=list,
        json_schema_extra={"example": ["https://agent.example.com/api/v1"]}
    )
    operational_bounds: Dict[str, Any] = Field(
        default_factory=dict,
        json_schema_extra={"example": {"max_tx_usd": 100000}}
    )


class AgentRegisterRequest(AgentManifestSchema):
    public_keys: List[PublicKeyRegisterRequest] = Field(
        ..., min_length=1, description="List of agent public keys (minimum 1 required)"
    )


class AgentResponse(BaseModel):
    id: str = Field(..., json_schema_extra={"example": "kya_agt_01h87z..."})
    status: AgentStatus
    owner_organization: str
    manifest: AgentManifestSchema
    manifest_hash: str
    public_keys: List[PublicKeyResponse]
    created_at: datetime
    updated_at: datetime


class AgentStatusUpdateRequest(BaseModel):
    status: AgentStatus = Field(..., description="Target status: SUSPENDED, REVOKED, ACTIVE")


class SignatureVerificationRequest(BaseModel):
    key_id: str = Field(..., description="SHA-256 fingerprint of the public key to verify against")
    message_base64: str = Field(..., description="Base64 encoded original payload message")
    signature_base64: str = Field(..., description="Base64 encoded digital signature")


class SignatureVerificationResponse(BaseModel):
    is_valid: bool
    agent_id: str
    owner_organization: str
    key_algorithm: str
