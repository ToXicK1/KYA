import pytest
from src.core.security import create_access_token, decode_access_token, SecurityException
from datetime import timedelta

def test_create_and_decode_valid_jwt():
    data = {"sub": "test_user", "org": "google_cloud", "roles": ["admin"]}
    token = create_access_token(data=data, expires_delta=timedelta(minutes=15))
    
    payload = decode_access_token(token)
    assert payload["sub"] == "test_user"
    assert payload["org"] == "google_cloud"
    assert "admin" in payload["roles"]

def test_expired_jwt_raises_security_exception():
    data = {"sub": "test_user"}
    # Token expired 10 minutes ago
    token = create_access_token(data=data, expires_delta=timedelta(minutes=-10))
    
    with pytest.raises(SecurityException):
        decode_access_token(token)

def test_invalid_signature_jwt_raises_security_exception():
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalidpayload.invalidsignature"
    with pytest.raises(SecurityException):
        decode_access_token(token)

def test_default_token_expiration():
    data = {"sub": "user_default_exp"}
    token = create_access_token(data=data)
    payload = decode_access_token(token)
    assert payload["sub"] == "user_default_exp"

@pytest.mark.asyncio
async def test_auth_token_endpoint_success(async_client):
    res = await async_client.post(
        "/api/v1/auth/token",
        json={
            "username": "admin_google",
            "password": "KYaSecureP@ssw0rd!2026",
            "organization": "org_google_cloud"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_auth_token_endpoint_invalid_credentials(async_client):
    res = await async_client.post(
        "/api/v1/auth/token",
        json={
            "username": "",
            "password": "",
            "organization": "org_google_cloud"
        }
    )
    assert res.status_code == 401
    assert "Invalid username or password" in res.json()["detail"]


@pytest.mark.asyncio
async def test_get_current_user_dependency_cases(auth_headers_invalid_sub):
    from src.presentation.api.dependencies import get_current_user
    from fastapi import HTTPException
    from fastapi.security import HTTPAuthorizationCredentials

    # Case 1: No credentials
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(None)
    assert exc_info.value.status_code == 401
    assert "Missing Authorization Bearer token header" in exc_info.value.detail

    # Case 2: Invalid sub
    token_str = auth_headers_invalid_sub["Authorization"].replace("Bearer ", "")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_str)
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(creds)
    assert exc_info.value.status_code == 401
    assert "Invalid token subject" in exc_info.value.detail

    # Case 3: Invalid token format
    creds_invalid = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid.jwt.token")
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(creds_invalid)
    assert exc_info.value.status_code == 401

