from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.domain.entities.agent import Agent
from src.domain.entities.manifest import AgentManifest
from src.domain.entities.public_key import PublicKey
from src.domain.value_objects.key_algorithm import KeyAlgorithm
from src.domain.interfaces.repositories import AgentRepositoryInterface
from src.domain.interfaces.crypto_verifier import CryptoVerifierInterface

@dataclass
class PublicKeyDTO:
    algorithm: KeyAlgorithm
    pem_content: str
    expires_at: Optional[datetime] = None

@dataclass
class RegisterAgentDTO:
    name: str
    version: str
    description: str
    owner_organization: str
    capabilities: List[str]
    endpoints: List[str]
    operational_bounds: Dict[str, Any]
    public_keys: List[PublicKeyDTO]

class RegisterAgentUseCase:
    def __init__(
        self,
        repository: AgentRepositoryInterface,
        crypto_verifier: CryptoVerifierInterface
    ):
        self._repository = repository
        self._crypto_verifier = crypto_verifier

    async def execute(self, dto: RegisterAgentDTO) -> Agent:
        # 1. Zero-Trust Private Key Guardrail & Public Key Validation
        validated_keys: List[PublicKey] = []
        for key_dto in dto.public_keys:
            # Enforce strictly no private key in payload
            self._crypto_verifier.assert_no_private_key(key_dto.pem_content)
            
            # Validate public key format & algorithm compatibility
            self._crypto_verifier.validate_public_key(key_dto.pem_content, key_dto.algorithm)
            
            # Construct Domain Entity for Public Key
            pk_entity = PublicKey.create(
                algorithm=key_dto.algorithm,
                pem_content=key_dto.pem_content,
                expires_at=key_dto.expires_at
            )
            validated_keys.append(pk_entity)

        # 2. Construct Agent Manifest
        manifest = AgentManifest(
            name=dto.name,
            version=dto.version,
            description=dto.description,
            owner_organization=dto.owner_organization,
            capabilities=dto.capabilities,
            endpoints=dto.endpoints,
            operational_bounds=dto.operational_bounds
        )

        # 3. Create Agent Aggregate Root
        agent = Agent.register(
            manifest=manifest,
            public_keys=validated_keys
        )

        # 4. Save to Repository
        return await self._repository.save(agent)
