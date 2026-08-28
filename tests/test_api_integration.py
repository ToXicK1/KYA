import pytest
import base64
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_check_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "agent-registry"

@pytest.mark.asyncio
async def test_auth_token_endpoint(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/auth/token",
        json={"username": "admin_test", "password": "pass", "organization": "org_google"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_register_and_get_agent_api(
    async_client: AsyncClient,
    valid_agent_payload: dict,
    auth_headers: dict
):
    # 1. Register Agent
    reg_res = await async_client.post(
        "/api/v1/agents",
        json=valid_agent_payload,
        headers=auth_headers
    )
    assert reg_res.status_code == 201
    agent_data = reg_res.json()
    agent_id = agent_data["id"]
    assert agent_id.startswith("kya_agt_")
    assert agent_data["status"] == "ACTIVE"
    assert len(agent_data["public_keys"]) == 1

    # 2. Get Agent Details
    get_res = await async_client.get(f"/api/v1/agents/{agent_id}")
    assert get_res.status_code == 200
    fetched_data = get_res.json()
    assert fetched_data["id"] == agent_id
    assert fetched_data["manifest"]["name"] == valid_agent_payload["name"]

@pytest.mark.asyncio
async def test_list_agents_api(
    async_client: AsyncClient,
    valid_agent_payload: dict,
    auth_headers: dict
):
    await async_client.post("/api/v1/agents", json=valid_agent_payload, headers=auth_headers)
    
    list_res = await async_client.get("/api/v1/agents?limit=10&offset=0")
    assert list_res.status_code == 200
    data = list_res.json()
    assert isinstance(data, list)
    assert len(data) >= 1

@pytest.mark.asyncio
async def test_update_agent_status_api(
    async_client: AsyncClient,
    valid_agent_payload: dict,
    auth_headers: dict
):
    reg_res = await async_client.post("/api/v1/agents", json=valid_agent_payload, headers=auth_headers)
    agent_id = reg_res.json()["id"]

    # Suspend
    suspend_res = await async_client.patch(
        f"/api/v1/agents/{agent_id}/status",
        json={"status": "SUSPENDED"},
        headers=auth_headers
    )
    assert suspend_res.status_code == 200
    assert suspend_res.json()["status"] == "SUSPENDED"

@pytest.mark.asyncio
async def test_verify_signature_api(
    async_client: AsyncClient,
    valid_agent_payload: dict,
    ed25519_keypair: tuple,
    auth_headers: dict
):
    reg_res = await async_client.post("/api/v1/agents", json=valid_agent_payload, headers=auth_headers)
    key_id = reg_res.json()["public_keys"][0]["key_id"]
    _, _, priv_key, _ = ed25519_keypair

    message = b"API Signature Verification Message Payload"
    signature = priv_key.sign(message)

    verify_res = await async_client.post(
        "/api/v1/agents/verify-signature",
        json={
            "key_id": key_id,
            "message_base64": base64.b64encode(message).decode('utf-8'),
            "signature_base64": base64.b64encode(signature).decode('utf-8')
        }
    )
    assert verify_res.status_code == 200
    res_data = verify_res.json()
    assert res_data["is_valid"] is True
    assert res_data["agent_id"] == reg_res.json()["id"]

@pytest.mark.asyncio
async def test_openapi_docs_and_redoc_endpoints(async_client: AsyncClient):
    docs_res = await async_client.get("/docs")
    assert docs_res.status_code == 200
    assert "text/html" in docs_res.headers["content-type"]
    assert "Swagger UI" in docs_res.text

    redoc_res = await async_client.get("/redoc")
    assert redoc_res.status_code == 200
    assert "text/html" in redoc_res.headers["content-type"]
    assert "ReDoc" in redoc_res.text

@pytest.mark.asyncio
async def test_main_startup_shutdown_events():
    from src.main import app, lifespan
    async with lifespan(app):
        pass

@pytest.mark.asyncio
async def test_middleware_exception_handling_branches(async_client: AsyncClient):
    from src.main import app
    from src.domain.exceptions import DomainException

    @app.get("/test-domain-exception")
    async def route_domain_exc():
        raise DomainException("Test domain exception message")

    @app.get("/test-unhandled-exception")
    async def route_unhandled_exc():
        raise RuntimeError("Test unhandled server exception")

    # DomainException -> 400 DOMAIN_ERROR
    res1 = await async_client.get("/test-domain-exception")
    assert res1.status_code == 400
    assert res1.json()["error"]["code"] == "DOMAIN_ERROR"

    # Runtime/Unhandled Exception -> 500 INTERNAL_SERVER_ERROR
    res2 = await async_client.get("/test-unhandled-exception")
    assert res2.status_code == 500
    assert res2.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"

@pytest.mark.asyncio
async def test_health_check_db_failure(async_client: AsyncClient):
    from src.main import app
    from src.core.database import get_db_session
    from unittest.mock import AsyncMock

    mock_session = AsyncMock()
    mock_session.execute.side_effect = Exception("DB Connection Lost")

    async def _override_broken_db():
        yield mock_session

    app.dependency_overrides[get_db_session] = _override_broken_db
    try:
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 503
        data = response.json()
        assert "Database probe failed" in data["detail"]
    finally:
        app.dependency_overrides.clear()



