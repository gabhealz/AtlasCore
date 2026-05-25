import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_login_invalid_email(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "invalid@domain.com", "password": "any"}
    )
    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "EMAIL_NOT_ALLOWED"

@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@healz.com.br", "password": "wrong_password"}
    )
    assert response.status_code == 401
    assert response.json()["detail"]["error_code"] == "INVALID_CREDENTIALS"

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@healz.com.br", "password": "admin"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
