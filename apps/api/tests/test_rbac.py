import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.auth import create_access_token
from app.core.permissions import (
    ROLE_PERMISSIONS_MATRIX,
    Permission,
    get_role_permissions,
    has_permission,
)
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
async def clean_engine() -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


def test_permission_matrix_all_roles() -> None:
    all_permissions = set(Permission)

    # 1. Super Admin has all permissions
    for perm in all_permissions:
        assert has_permission(UserRole.SUPER_ADMIN, perm)

    # 2. Admin has all permissions
    for perm in all_permissions:
        assert has_permission(UserRole.ADMIN, perm)

    # 3. Researcher permissions check
    assert has_permission(UserRole.RESEARCHER, Permission.ASSETS_UPLOAD)
    assert has_permission(UserRole.RESEARCHER, Permission.ASSETS_EDIT_OWN)
    assert has_permission(UserRole.RESEARCHER, Permission.ASSETS_EDIT_METADATA)
    assert has_permission(UserRole.RESEARCHER, Permission.SEARCH_USE)
    assert has_permission(UserRole.RESEARCHER, Permission.AI_USE)
    assert has_permission(UserRole.RESEARCHER, Permission.EXPORTS_FULL)
    assert has_permission(UserRole.RESEARCHER, Permission.EXPORTS_WATERMARKED)
    assert not has_permission(UserRole.RESEARCHER, Permission.ASSETS_EDIT_ANY)
    assert not has_permission(UserRole.RESEARCHER, Permission.CLAIMS_VERIFY)
    assert not has_permission(UserRole.RESEARCHER, Permission.AUDIT_VIEW)
    assert not has_permission(UserRole.RESEARCHER, Permission.USERS_MANAGE)

    # 4. Reviewer permissions check
    assert has_permission(UserRole.REVIEWER, Permission.CLAIMS_VERIFY)
    assert has_permission(UserRole.REVIEWER, Permission.ASSETS_EDIT_METADATA)
    assert has_permission(UserRole.REVIEWER, Permission.SEARCH_USE)
    assert has_permission(UserRole.REVIEWER, Permission.AI_USE)
    assert has_permission(UserRole.REVIEWER, Permission.EXPORTS_WATERMARKED)
    assert not has_permission(UserRole.REVIEWER, Permission.ASSETS_UPLOAD)
    assert not has_permission(UserRole.REVIEWER, Permission.ASSETS_EDIT_ANY)
    assert not has_permission(UserRole.REVIEWER, Permission.ASSETS_EDIT_OWN)
    assert not has_permission(UserRole.REVIEWER, Permission.EXPORTS_FULL)
    assert not has_permission(UserRole.REVIEWER, Permission.AUDIT_VIEW)
    assert not has_permission(UserRole.REVIEWER, Permission.USERS_MANAGE)

    # 5. Contributor permissions check
    assert has_permission(UserRole.CONTRIBUTOR, Permission.ASSETS_UPLOAD)
    assert has_permission(UserRole.CONTRIBUTOR, Permission.ASSETS_EDIT_OWN)
    assert has_permission(UserRole.CONTRIBUTOR, Permission.SEARCH_USE)
    assert has_permission(UserRole.CONTRIBUTOR, Permission.EXPORTS_WATERMARKED)
    assert not has_permission(UserRole.CONTRIBUTOR, Permission.ASSETS_EDIT_METADATA)
    assert not has_permission(UserRole.CONTRIBUTOR, Permission.CLAIMS_VERIFY)
    assert not has_permission(UserRole.CONTRIBUTOR, Permission.AI_USE)
    assert not has_permission(UserRole.CONTRIBUTOR, Permission.EXPORTS_FULL)
    assert not has_permission(UserRole.CONTRIBUTOR, Permission.AUDIT_VIEW)
    assert not has_permission(UserRole.CONTRIBUTOR, Permission.USERS_MANAGE)

    # 6. Viewer permissions check
    assert has_permission(UserRole.VIEWER, Permission.SEARCH_USE)
    assert has_permission(UserRole.VIEWER, Permission.EXPORTS_WATERMARKED)
    assert not has_permission(UserRole.VIEWER, Permission.ASSETS_UPLOAD)
    assert not has_permission(UserRole.VIEWER, Permission.ASSETS_EDIT_ANY)
    assert not has_permission(UserRole.VIEWER, Permission.ASSETS_EDIT_OWN)
    assert not has_permission(UserRole.VIEWER, Permission.ASSETS_EDIT_METADATA)
    assert not has_permission(UserRole.VIEWER, Permission.CLAIMS_VERIFY)
    assert not has_permission(UserRole.VIEWER, Permission.AI_USE)
    assert not has_permission(UserRole.VIEWER, Permission.EXPORTS_FULL)
    assert not has_permission(UserRole.VIEWER, Permission.AUDIT_VIEW)
    assert not has_permission(UserRole.VIEWER, Permission.USERS_MANAGE)

    # Verify get_role_permissions helper
    for role in UserRole:
        perms = get_role_permissions(role)
        assert set(perms) == ROLE_PERMISSIONS_MATRIX[role]


@pytest.mark.asyncio
async def test_me_unauthenticated_returns_401() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/me")
        assert response.status_code == 401
        assert "Missing authentication" in response.json()["detail"]


@pytest.mark.asyncio
async def test_me_invalid_token_returns_401() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/me",
            headers={"Authorization": "Bearer invalid_garbage_token"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_valid_user_returns_200() -> None:
    clerk_id = f"user_{uuid.uuid4().hex[:12]}"
    email = f"analyst_{uuid.uuid4().hex[:8]}@example.com"

    async with AsyncSessionLocal() as session:
        user = User(
            clerk_user_id=clerk_id,
            email=email,
            full_name="Senior Analyst",
            role=UserRole.RESEARCHER,
            is_active=True,
        )
        session.add(user)
        await session.commit()

    token = create_access_token({"sub": clerk_id, "email": email})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == email
        assert data["role"] == "researcher"
        assert "assets:upload" in data["permissions"]
        assert "search:use" in data["permissions"]
        assert "users:manage" not in data["permissions"]


@pytest.mark.asyncio
async def test_me_deactivated_user_returns_403() -> None:
    clerk_id = f"user_{uuid.uuid4().hex[:12]}"
    email = f"deactivated_{uuid.uuid4().hex[:8]}@example.com"

    async with AsyncSessionLocal() as session:
        user = User(
            clerk_user_id=clerk_id,
            email=email,
            full_name="Deactivated User",
            role=UserRole.VIEWER,
            is_active=False,
        )
        session.add(user)
        await session.commit()

    token = create_access_token({"sub": clerk_id, "email": email})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        assert "deactivated" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_me_revoked_user_returns_403() -> None:
    clerk_id = f"user_{uuid.uuid4().hex[:12]}"
    email = f"revoked_{uuid.uuid4().hex[:8]}@example.com"

    async with AsyncSessionLocal() as session:
        user = User(
            clerk_user_id=clerk_id,
            email=email,
            full_name="Revoked User",
            role=UserRole.CONTRIBUTOR,
            is_active=True,
            revoked_at=datetime.now(UTC),
        )
        session.add(user)
        await session.commit()

    token = create_access_token({"sub": clerk_id, "email": email})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        assert "revoked" in response.json()["detail"].lower()
