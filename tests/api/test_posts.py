# tests/api/test_posts.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from app.core.auth import create_access_token
from app.db.models import User, UserRole

@pytest.fixture
def test_user(db_session: AsyncSession) -> User:
    user = User(
        email="postuser@example.com",
        username="postuser",
        hashed_password="hashed_password",
        role=UserRole.GENERAL,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def auth_headers(test_user: User) -> dict:
    token = create_access_token(
        user=test_user
    )
    print(token)
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_create_post(client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
    post_data = {
        "content": "This is a test post from pytest!",
        "privacy": "public"
    }
    response = await client.post("/api/v1/posts/", json=post_data, headers=auth_headers)
    print(response.json())
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["content"] == post_data["content"]
    assert "author" in data
    assert data["author"]["username"] == "postuser"