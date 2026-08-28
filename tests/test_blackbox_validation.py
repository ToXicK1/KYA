import pytest
import base64
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_blackbox_reject_private_key_payload(
    async_client: AsyncClient,
    ed25519_keypair: tuple,
    auth_headers: dict
):
    _, priv_pem, _, _ = ed25519_keypair
    payload = {
        "name": "Malicious Agent",
        "version": "1.0",
        "description": "Desc",
        "owner_organization": "org_bad",
        "capabilities": [],
        "endpoints": [],
        "operational_bounds": {},
        "public_keys": [
            {
                "algorithm": "ED25519",
                "pem_content": priv_pem  # PRIVATE KEY SUBMITTED!
            }
        ]
    }

    res = await async_client.post("/api/v1/agents", json=payload, headers=auth_headers)
    assert res.status_code == 400
    err = res.json()
    assert err["error"]["code"] == "PRIVATE_KEY_FORBIDDEN"

@pytest.mark.asyncio
async def test_blackbox_missing_required_fields(
    async_client: AsyncClient,
    auth_headers: dict
):
    payload = {"name": "Incomplete Agent"}  # Missing version, owner_org, public_keys
    res = await async_client.post("/api/v1/agents", json=payload, headers=auth_headers)
    assert res.status_code == 422  # Unprocessable Entity

@pytest.mark.asyncio
async def test_blackbox_invalid_public_key_pem(
    async_client: AsyncClient,
    auth_headers: dict
):
    payload = {
        "name": "Bad Key Agent",
        "version": "1.0",
        "description": "Desc",
        "owner_organization": "org_test",
        "capabilities": [],
        "endpoints": [],
        "operational_bounds": {},
        "public_keys": [
            {
                "algorithm": "ED25519",
                "pem_content": "-----BEGIN PUBLIC KEY-----\nNOT_VALID_BASE64_PEM\n-----END PUBLIC KEY-----"
            }
        ]
    }
    res = await async_client.post("/api/v1/agents", json=payload, headers=auth_headers)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_PUBLIC_KEY"

@pytest.mark.asyncio
async def test_blackbox_nonexistent_agent_404(async_client: AsyncClient):
    res = await async_client.get("/api/v1/agents/kya_agt_00000000000000000000000000")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "AGENT_NOT_FOUND"

@pytest.mark.asyncio
async def test_blackbox_invalid_base64_signature(async_client: AsyncClient):
    res = await async_client.post(
        "/api/v1/agents/verify-signature",
        json={
            "key_id": "nonexistent_key_id",
            "message_base64": "invalid_base64!!!",
            "signature_base64": "invalid_base64!!!"
        }
    )
    assert res.status_code in (400, 404)

@pytest.mark.asyncio
async def test_blackbox_pagination_boundary_limits(async_client: AsyncClient):
    # limit out of bounds (< 1)
    res1 = await async_client.get("/api/v1/agents?limit=0")
    assert res1.status_code == 422

    # limit out of bounds (> 100)
    res2 = await async_client.get("/api/v1/agents?limit=101")
    assert res2.status_code == 422

    # offset out of bounds (< 0)
    res3 = await async_client.get("/api/v1/agents?offset=-1")
    assert res3.status_code == 422

    # Valid boundary limits
    res4 = await async_client.get("/api/v1/agents?limit=1&offset=0")
    assert res4.status_code == 200
    res5 = await async_client.get("/api/v1/agents?limit=100&offset=0")
    assert res5.status_code == 200

@pytest.mark.asyncio
async def test_blackbox_invalid_enum_algorithm(
    async_client: AsyncClient,
    auth_headers: dict
):
    payload = {
        "name": "Invalid Enum Agent",
        "version": "1.0",
        "owner_organization": "org_test",
        "public_keys": [
            {
                "algorithm": "UNSUPPORTED_ALGO_999",
                "pem_content": "some_pem"
            }
        ]
    }
    res = await async_client.post("/api/v1/agents", json=payload, headers=auth_headers)
    assert res.status_code == 422

@pytest.mark.asyncio
async def test_blackbox_duplicate_agent_registration(
    async_client: AsyncClient,
    valid_agent_payload: dict,
    auth_headers: dict
):
    res1 = await async_client.post("/api/v1/agents", json=valid_agent_payload, headers=auth_headers)
    assert res1.status_code == 201

    # Re-registering with exact same public key conflicts with database key uniqueness constraint
    res2 = await async_client.post("/api/v1/agents", json=valid_agent_payload, headers=auth_headers)
    assert res2.status_code in (400, 500)



