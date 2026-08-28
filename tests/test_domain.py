import pytest
from datetime import datetime, timezone
from src.domain.value_objects.agent_id import AgentId
from src.domain.value_objects.agent_status import AgentStatus
from src.domain.value_objects.key_algorithm import KeyAlgorithm
from src.domain.entities.manifest import AgentManifest
from src.domain.entities.public_key import PublicKey
from src.domain.entities.agent import Agent
from src.domain.exceptions import (
    DomainException,
    AgentNotFoundException,
    AgentAlreadyExistsException,
    InvalidPublicKeyException,
    PrivateKeyDetectedException,
    InvalidAgentStatusException
)

def test_agent_id_validations():
    # Valid generation
    aid = AgentId.generate()
    assert aid.value.startswith("kya_agt_")
    assert str(aid) == aid.value

    # Invalid prefix
    with pytest.raises(ValueError, match="AgentId must start with"):
        AgentId(value="invalid_prefix_123456789")

    # Short value
    with pytest.raises(ValueError, match="AgentId format is invalid"):
        AgentId(value="kya_agt_short")

def test_manifest_hash_reproducibility():
    manifest1 = AgentManifest(
        name="Agent A",
        version="1.0",
        description="Desc",
        owner_organization="org1",
        capabilities=["read"],
        endpoints=["https://e1.com"],
        operational_bounds={"limit": 100}
    )
    manifest2 = AgentManifest(
        name="Agent A",
        version="1.0",
        description="Desc",
        owner_organization="org1",
        capabilities=["read"],
        endpoints=["https://e1.com"],
        operational_bounds={"limit": 100}
    )
    assert manifest1.compute_hash() == manifest2.compute_hash()

def test_public_key_entity_fingerprint():
    pem = "-----BEGIN PUBLIC KEY-----\nTEST_KEY_CONTENT\n-----END PUBLIC KEY-----"
    pk = PublicKey.create(algorithm=KeyAlgorithm.ED25519, pem_content=pem)
    assert len(pk.key_id) == 64  # SHA-256 hex string length
    assert pk.is_active is True

def test_agent_aggregate_state_transitions():
    manifest = AgentManifest(
        name="Agent B",
        version="2.0",
        description="Desc B",
        owner_organization="org2",
        capabilities=[],
        endpoints=[],
        operational_bounds={}
    )
    pk = PublicKey.create(algorithm=KeyAlgorithm.RSA_4096, pem_content="dummy_pem")
    agent = Agent.register(manifest=manifest, public_keys=[pk])

    # Initial state
    assert agent.status == AgentStatus.ACTIVE
    assert len(agent.public_keys) == 1

    # Suspend
    agent.suspend()
    assert agent.status == AgentStatus.SUSPENDED

    # Activate
    agent.activate()
    assert agent.status == AgentStatus.ACTIVE

    # Revoke
    agent.revoke()
    assert agent.status == AgentStatus.REVOKED
    assert agent.public_keys[0].is_active is False

    # Cannot reactivate or suspend revoked agent
    with pytest.raises(InvalidAgentStatusException):
        agent.activate()

    with pytest.raises(InvalidAgentStatusException):
        agent.suspend()

def test_domain_exception_messages():
    e1 = AgentNotFoundException("kya_agt_999")
    assert "kya_agt_999" in str(e1)

    e2 = AgentAlreadyExistsException("kya_agt_888")
    assert "kya_agt_888" in str(e2)

    e3 = InvalidPublicKeyException("Malformed RSA key")
    assert "Malformed RSA key" in str(e3)

    e4 = PrivateKeyDetectedException()
    assert "forbidden" in str(e4).lower()

    e5 = InvalidAgentStatusException("REVOKED", "ACTIVE")
    assert "REVOKED" in str(e5)

    base_e = DomainException("Generic domain error")
    assert str(base_e) == "Generic domain error"

def test_agent_default_datetime():
    from src.domain.entities.agent import _now_utc
    now = _now_utc()
    assert isinstance(now, datetime)
    assert now.tzinfo == timezone.utc

@pytest.mark.asyncio
async def test_domain_abstract_interfaces():
    from src.domain.interfaces.crypto_verifier import CryptoVerifierInterface
    from src.domain.interfaces.repositories import AgentRepositoryInterface
    from src.domain.value_objects.key_algorithm import KeyAlgorithm
    from src.domain.value_objects.agent_id import AgentId

    class ConcreteCryptoVerifier(CryptoVerifierInterface):
        def assert_no_private_key(self, pem_content: str) -> None:
            super().assert_no_private_key(pem_content)

        def validate_public_key(self, pem_content: str, algorithm: KeyAlgorithm) -> bool:
            return super().validate_public_key(pem_content, algorithm)

        def verify_signature(self, pem_content: str, message: bytes, signature: bytes) -> bool:
            return super().verify_signature(pem_content, message, signature)

    class ConcreteRepository(AgentRepositoryInterface):
        async def save(self, agent):
            return await super().save(agent)

        async def get_by_id(self, agent_id: AgentId):
            return await super().get_by_id(agent_id)

        async def get_by_key_id(self, key_id: str):
            return await super().get_by_key_id(key_id)

        async def list(self, limit=50, offset=0, status=None, owner_organization=None):
            return await super().list(limit, offset, status, owner_organization)

        async def update_status(self, agent_id: AgentId, status):
            return await super().update_status(agent_id, status)

    verifier = ConcreteCryptoVerifier()
    verifier.assert_no_private_key("pem")
    verifier.validate_public_key("pem", KeyAlgorithm.ED25519)
    verifier.verify_signature("pem", b"msg", b"sig")

    repo = ConcreteRepository()
    await repo.save(None)
    await repo.get_by_id(AgentId.generate())
    await repo.get_by_key_id("key_id")
    await repo.list()
    await repo.update_status(AgentId.generate(), AgentStatus.ACTIVE)

