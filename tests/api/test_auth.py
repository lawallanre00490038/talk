# tests/api/test_auth.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, db_session: AsyncSession):
    user_data = {
        "full_name": "Test User",
        "username": "testuser",
        "email": "test@example.com",
        "password": "strongpassword"
    }
    response = await client.post("/api/v1/auth/register", data=user_data)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == user_data["email"]
    assert "id" in data

@pytest.mark.asyncio
async def test_login_for_access_token(client: AsyncClient, db_session: AsyncSession):
    # First, register a user
    user_data = {
        "full_name": "loginuser User",
        "username": "loginuser",
        "email": "login@example.com",
        "password": "strongpassword"
    }
    await client.post("/api/v1/auth/register", data=user_data)

    # Then, try to log in
    login_data = {
        "email": "login@example.com",
        "username": "loginuser",
        "password": "strongpassword"
    }
    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK
    print(f"response.json() = {response.json()}\n\n\n\n")
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"