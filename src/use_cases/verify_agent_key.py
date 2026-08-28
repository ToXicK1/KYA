from dataclasses import dataclass
from src.domain.interfaces.repositories import AgentRepositoryInterface
from src.domain.interfaces.crypto_verifier import CryptoVerifierInterface
from src.domain.value_objects.agent_status import AgentStatus
from src.domain.exceptions import AgentNotFoundException, DomainException

@dataclass
class SignatureVerificationDTO:
    key_id: str
    message: bytes
    signature: bytes

@dataclass
class SignatureVerificationResult:
    is_valid: bool
    agent_id: str
    owner_organization: str
    key_algorithm: str

class VerifyAgentSignatureUseCase:
    def __init__(
        self,
        repository: AgentRepositoryInterface,
        crypto_verifier: CryptoVerifierInterface
    ):
        self._repository = repository
        self._crypto_verifier = crypto_verifier

    async def execute(self, dto: SignatureVerificationDTO) -> SignatureVerificationResult:
        agent = await self._repository.get_by_key_id(dto.key_id)
        if not agent:
            raise AgentNotFoundException(f"key_id:{dto.key_id}")

        if agent.status != AgentStatus.ACTIVE:
            raise DomainException(f"Agent '{agent.id.value}' is not ACTIVE (status: {agent.status.value}). Signature rejected.")

        target_key = next((k for k in agent.public_keys if k.key_id == dto.key_id), None)
        if not target_key or not target_key.is_active:
            raise DomainException(f"Public key '{dto.key_id}' is revoked or inactive.")

        is_valid = self._crypto_verifier.verify_signature(
            pem_content=target_key.pem_content,
            message=dto.message,
            signature=dto.signature
        )

        return SignatureVerificationResult(
            is_valid=is_valid,
            agent_id=agent.id.value,
            owner_organization=agent.owner_organization,
            key_algorithm=target_key.algorithm.value
        )
