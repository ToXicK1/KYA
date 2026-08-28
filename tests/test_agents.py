import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.hazmat.primitives import serialization
from src.infrastructure.crypto.key_verifier_service import PyCAKeyVerifierService
from src.domain.value_objects.key_algorithm import KeyAlgorithm
from src.domain.value_objects.agent_id import AgentId
from src.domain.value_objects.agent_status import AgentStatus
from src.domain.entities.manifest import AgentManifest
from src.domain.entities.agent import Agent
from src.domain.entities.public_key import PublicKey
from src.domain.exceptions import PrivateKeyDetectedException, InvalidAgentStatusException

def generate_test_keys():
    # Ed25519
    ed_priv = ed25519.Ed25519PrivateKey.generate()
    ed_pub = ed_priv.public_key()
    
    ed_pub_pem = ed_pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    ed_priv_pem = ed_priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')

    return ed_pub_pem, ed_priv_pem, ed_priv, ed_pub

def test_agent_id_generation():
    agent_id = AgentId.generate()
    assert agent_id.value.startswith("kya_agt_")
    assert str(agent_id) == agent_id.value

def test_assert_no_private_key_rejects_private_key():
    _, ed_priv_pem, _, _ = generate_test_keys()
    verifier = PyCAKeyVerifierService()
    
    with pytest.raises(PrivateKeyDetectedException):
        verifier.assert_no_private_key(ed_priv_pem)

def test_assert_no_private_key_accepts_valid_public_key():
    ed_pub_pem, _, _, _ = generate_test_keys()
    verifier = PyCAKeyVerifierService()
    
    # Should not raise any exception
    verifier.assert_no_private_key(ed_pub_pem)
    assert verifier.validate_public_key(ed_pub_pem, KeyAlgorithm.ED25519) is True

def test_signature_verification_success():
    ed_pub_pem, _, ed_priv, _ = generate_test_keys()
    verifier = PyCAKeyVerifierService()
    
    message = b"KYA Transaction Request #10042"
    signature = ed_priv.sign(message)
    
    is_valid = verifier.verify_signature(ed_pub_pem, message, signature)
    assert is_valid is True

def test_agent_status_transitions():
    manifest = AgentManifest(
        name="Test Agent",
        version="1.0",
        description="Desc",
        owner_organization="org_test",
        capabilities=["read"],
        endpoints=["https://test.com"],
        operational_bounds={}
    )
    agent = Agent.register(manifest=manifest, public_keys=[])
    assert agent.status == AgentStatus.ACTIVE

    agent.suspend()
    assert agent.status == AgentStatus.SUSPENDED

    agent.revoke()
    assert agent.status == AgentStatus.REVOKED

    # Reactivating revoked agent must fail
    with pytest.raises(InvalidAgentStatusException):
        agent.activate()

@pytest.mark.asyncio
async def test_list_agents_filtering_api(
    async_client,
    valid_agent_payload: dict,
    auth_headers: dict
):
    # Register an agent
    reg_res = await async_client.post("/api/v1/agents", json=valid_agent_payload, headers=auth_headers)
    assert reg_res.status_code == 201
    
    # Filter by status and owner_organization
    res = await async_client.get("/api/v1/agents?status=ACTIVE&owner_organization=org_google_finance")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["status"] == "ACTIVE"
    assert data[0]["owner_organization"] == "org_google_finance"

    # Filter with non-matching org
    res_empty = await async_client.get("/api/v1/agents?status=SUSPENDED&owner_organization=non_existent_org")
    assert res_empty.status_code == 200
    assert len(res_empty.json()) == 0

