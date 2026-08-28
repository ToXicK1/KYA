import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from src.infrastructure.db.repositories.postgres_agent_repository import PostgresAgentRepository
from src.infrastructure.crypto.key_verifier_service import PyCAKeyVerifierService
from src.use_cases.register_agent import RegisterAgentUseCase, RegisterAgentDTO, PublicKeyDTO
from src.use_cases.get_agent import GetAgentUseCase
from src.use_cases.verify_agent_key import VerifyAgentSignatureUseCase, SignatureVerificationDTO
from src.use_cases.list_agents import ListAgentsUseCase
from src.use_cases.update_agent_status import UpdateAgentStatusUseCase
from src.domain.value_objects.key_algorithm import KeyAlgorithm
from src.domain.value_objects.agent_status import AgentStatus
from src.domain.exceptions import AgentNotFoundException, DomainException

@pytest.mark.asyncio
async def test_register_and_get_agent_use_case(test_db_session, ed25519_keypair):
    repo = PostgresAgentRepository(test_db_session)
    crypto = PyCAKeyVerifierService()
    pub_pem, _, _, _ = ed25519_keypair

    register_uc = RegisterAgentUseCase(repo, crypto)
    get_uc = GetAgentUseCase(repo)

    dto = RegisterAgentDTO(
        name="UseCase Test Agent",
        version="1.0.0",
        description="Testing Use Case Layer",
        owner_organization="org_test_uc",
        capabilities=["cap1", "cap2"],
        endpoints=["https://uc.example.com"],
        operational_bounds={"limit": 50},
        public_keys=[
            PublicKeyDTO(algorithm=KeyAlgorithm.ED25519, pem_content=pub_pem)
        ]
    )

    created_agent = await register_uc.execute(dto)
    assert created_agent.id.value.startswith("kya_agt_")
    assert created_agent.manifest.name == "UseCase Test Agent"
    assert created_agent.status == AgentStatus.ACTIVE

    fetched_agent = await get_uc.execute(created_agent.id.value)
    assert fetched_agent.id.value == created_agent.id.value
    assert fetched_agent.owner_organization == "org_test_uc"

@pytest.mark.asyncio
async def test_get_nonexistent_agent_raises_exception(test_db_session):
    repo = PostgresAgentRepository(test_db_session)
    get_uc = GetAgentUseCase(repo)

    with pytest.raises(AgentNotFoundException):
        await get_uc.execute("kya_agt_nonexistent_99999")

@pytest.mark.asyncio
async def test_list_agents_use_case(test_db_session):
    repo = PostgresAgentRepository(test_db_session)
    crypto = PyCAKeyVerifierService()
    register_uc = RegisterAgentUseCase(repo, crypto)
    list_uc = ListAgentsUseCase(repo)

    # Register 2 agents each with a UNIQUE key to avoid fingerprint collision
    for i in range(2):
        fresh_priv = ed25519.Ed25519PrivateKey.generate()
        fresh_pub_pem = fresh_priv.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        dto = RegisterAgentDTO(
            name=f"List Agent {i}",
            version="1.0",
            description="Desc",
            owner_organization="org_list",
            capabilities=[],
            endpoints=[],
            operational_bounds={},
            public_keys=[PublicKeyDTO(algorithm=KeyAlgorithm.ED25519, pem_content=fresh_pub_pem)]
        )
        await register_uc.execute(dto)

    agents = await list_uc.execute(limit=10, offset=0, owner_organization="org_list")
    assert len(agents) == 2

@pytest.mark.asyncio
async def test_update_agent_status_use_case(test_db_session, ed25519_keypair):
    repo = PostgresAgentRepository(test_db_session)
    crypto = PyCAKeyVerifierService()
    pub_pem, _, _, _ = ed25519_keypair

    register_uc = RegisterAgentUseCase(repo, crypto)
    update_uc = UpdateAgentStatusUseCase(repo)
    get_uc = GetAgentUseCase(repo)

    dto = RegisterAgentDTO(
        name="Status Test Agent",
        version="1.0",
        description="Desc",
        owner_organization="org_status",
        capabilities=[],
        endpoints=[],
        operational_bounds={},
        public_keys=[PublicKeyDTO(algorithm=KeyAlgorithm.ED25519, pem_content=pub_pem)]
    )
    agent = await register_uc.execute(dto)

    # Suspend
    suspended_agent = await update_uc.execute(agent.id.value, AgentStatus.SUSPENDED)
    assert suspended_agent.status == AgentStatus.SUSPENDED

    # Reactivate
    active_agent = await update_uc.execute(agent.id.value, AgentStatus.ACTIVE)
    assert active_agent.status == AgentStatus.ACTIVE

    # Revoke
    revoked_agent = await update_uc.execute(agent.id.value, AgentStatus.REVOKED)
    assert revoked_agent.status == AgentStatus.REVOKED

@pytest.mark.asyncio
async def test_verify_agent_signature_use_case(test_db_session, ed25519_keypair):
    repo = PostgresAgentRepository(test_db_session)
    crypto = PyCAKeyVerifierService()
    pub_pem, _, priv_key, _ = ed25519_keypair

    register_uc = RegisterAgentUseCase(repo, crypto)
    verify_uc = VerifyAgentSignatureUseCase(repo, crypto)

    dto = RegisterAgentDTO(
        name="Verify Sig Agent",
        version="1.0",
        description="Desc",
        owner_organization="org_sig",
        capabilities=[],
        endpoints=[],
        operational_bounds={},
        public_keys=[PublicKeyDTO(algorithm=KeyAlgorithm.ED25519, pem_content=pub_pem)]
    )
    agent = await register_uc.execute(dto)
    key_id = agent.public_keys[0].key_id

    message = b"Transaction #9001"
    signature = priv_key.sign(message)

    sig_dto = SignatureVerificationDTO(key_id=key_id, message=message, signature=signature)
    result = await verify_uc.execute(sig_dto)

    assert result.is_valid is True
    assert result.agent_id == agent.id.value
    assert result.owner_organization == "org_sig"

@pytest.mark.asyncio
async def test_verify_signature_suspended_agent_fails(test_db_session, ed25519_keypair):
    repo = PostgresAgentRepository(test_db_session)
    crypto = PyCAKeyVerifierService()
    pub_pem, _, priv_key, _ = ed25519_keypair

    register_uc = RegisterAgentUseCase(repo, crypto)
    update_uc = UpdateAgentStatusUseCase(repo)
    verify_uc = VerifyAgentSignatureUseCase(repo, crypto)

    dto = RegisterAgentDTO(
        name="Suspended Agent",
        version="1.0",
        description="Desc",
        owner_organization="org_sig",
        capabilities=[],
        endpoints=[],
        operational_bounds={},
        public_keys=[PublicKeyDTO(algorithm=KeyAlgorithm.ED25519, pem_content=pub_pem)]
    )
    agent = await register_uc.execute(dto)
    await update_uc.execute(agent.id.value, AgentStatus.SUSPENDED)

    sig_dto = SignatureVerificationDTO(
        key_id=agent.public_keys[0].key_id,
        message=b"Msg",
        signature=priv_key.sign(b"Msg")
    )

    with pytest.raises(DomainException, match="not ACTIVE"):
        await verify_uc.execute(sig_dto)

@pytest.mark.asyncio
async def test_update_status_nonexistent_agent_raises_exception(test_db_session):
    repo = PostgresAgentRepository(test_db_session)
    update_uc = UpdateAgentStatusUseCase(repo)

    with pytest.raises(AgentNotFoundException):
        await update_uc.execute("kya_agt_nonexistent_99999", AgentStatus.SUSPENDED)

@pytest.mark.asyncio
async def test_verify_signature_nonexistent_key_raises_exception(test_db_session):
    repo = PostgresAgentRepository(test_db_session)
    crypto = PyCAKeyVerifierService()
    verify_uc = VerifyAgentSignatureUseCase(repo, crypto)

    sig_dto = SignatureVerificationDTO(
        key_id="nonexistent_key_id_999",
        message=b"Msg",
        signature=b"Sig"
    )

    with pytest.raises(AgentNotFoundException):
        await verify_uc.execute(sig_dto)

@pytest.mark.asyncio
async def test_verify_signature_revoked_key_raises_exception(test_db_session, ed25519_keypair):
    repo = PostgresAgentRepository(test_db_session)
    crypto = PyCAKeyVerifierService()
    pub_pem, _, priv_key, _ = ed25519_keypair

    register_uc = RegisterAgentUseCase(repo, crypto)
    update_uc = UpdateAgentStatusUseCase(repo)
    verify_uc = VerifyAgentSignatureUseCase(repo, crypto)

    dto = RegisterAgentDTO(
        name="Revoked Agent",
        version="1.0",
        description="Desc",
        owner_organization="org_sig",
        capabilities=[],
        endpoints=[],
        operational_bounds={},
        public_keys=[PublicKeyDTO(algorithm=KeyAlgorithm.ED25519, pem_content=pub_pem)]
    )
    agent = await register_uc.execute(dto)
    await update_uc.execute(agent.id.value, AgentStatus.REVOKED)

    sig_dto = SignatureVerificationDTO(
        key_id=agent.public_keys[0].key_id,
        message=b"Msg",
        signature=priv_key.sign(b"Msg")
    )

    # When revoked, agent status is REVOKED, and key.is_active is False
    with pytest.raises(DomainException):
        await verify_uc.execute(sig_dto)

@pytest.mark.asyncio
async def test_postgres_repository_direct_methods(test_db_session):
    from src.domain.value_objects.agent_id import AgentId
    from src.domain.value_objects.agent_status import AgentStatus
    repo = PostgresAgentRepository(test_db_session)

    # update_status on non-existent agent returns False
    res = await repo.update_status(AgentId.generate(), AgentStatus.SUSPENDED)
    assert res is False

    # get_by_key_id on non-existent key returns None
    key_agent = await repo.get_by_key_id("nonexistent_key_123")
    assert key_agent is None

@pytest.mark.asyncio
async def test_verify_signature_inactive_key_on_active_agent(test_db_session, ed25519_keypair):
    repo = PostgresAgentRepository(test_db_session)
    crypto = PyCAKeyVerifierService()
    pub_pem, _, priv_key, _ = ed25519_keypair

    register_uc = RegisterAgentUseCase(repo, crypto)
    verify_uc = VerifyAgentSignatureUseCase(repo, crypto)

    dto = RegisterAgentDTO(
        name="Inactive Key Agent",
        version="1.0",
        description="Desc",
        owner_organization="org_sig",
        capabilities=[],
        endpoints=[],
        operational_bounds={},
        public_keys=[PublicKeyDTO(algorithm=KeyAlgorithm.ED25519, pem_content=pub_pem)]
    )
    agent = await register_uc.execute(dto)
    # Manually deactivate key while keeping agent active
    agent.public_keys[0].is_active = False
    await repo.save(agent)

    sig_dto = SignatureVerificationDTO(
        key_id=agent.public_keys[0].key_id,
        message=b"Msg",
        signature=priv_key.sign(b"Msg")
    )

    with pytest.raises(DomainException, match="revoked or inactive"):
        await verify_uc.execute(sig_dto)



