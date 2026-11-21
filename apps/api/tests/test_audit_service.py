import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.auth import create_access_token
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.user import User, UserRole
from app.services.audit import AuditService


@pytest.fixture(autouse=True)
async def clean_engine() -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_audit_service_record_and_list() -> None:
    async with AsyncSessionLocal() as session:
        # Create actor user
        actor = User(
            clerk_user_id=f"user_{uuid.uuid4().hex[:12]}",
            email=f"actor_{uuid.uuid4().hex[:8]}@example.com",
            full_name="Audit Actor",
            role=UserRole.ADMIN,
        )
        session.add(actor)
        await session.commit()

        # Record multiple actions
        log1 = await AuditService.record(
            db=session,
            actor_id=actor.id,
            action="asset.upload",
            resource_type="asset",
            resource_id="doc-001",
            metadata={"filename": "report.pdf"},
            ip_address="10.0.0.1",
        )
        await session.commit()

        assert log1.id is not None
        assert log1.actor_user_id == actor.id
        assert log1.action == "asset.upload"
        assert log1.created_at is not None

        log2 = await AuditService.record(
            db=session,
            actor_id=actor.id,
            action="asset.download",
            resource_type="asset",
            resource_id="doc-001",
            metadata={"format": "pdf"},
            ip_address="10.0.0.2",
        )
        await session.commit()
        assert log2.action == "asset.download"

        # List logs
        logs, total = await AuditService.list_logs(
            db=session, limit=10, offset=0, actor_id=actor.id
        )
        assert total >= 2
        actions = [item.action for item in logs]
        assert "asset.upload" in actions
        assert "asset.download" in actions


@pytest.mark.asyncio
async def test_get_audit_logs_role_permissions() -> None:
    transport = ASGITransport(app=app)

    # 1. Unauthenticated -> 401
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/audit-logs")
        assert resp.status_code == 401

    # Create users with all 6 roles
    roles_users: dict[UserRole, tuple[str, str]] = {}
    async with AsyncSessionLocal() as session:
        for role in UserRole:
            clerk_id = f"user_{role.value}_{uuid.uuid4().hex[:8]}"
            email = f"{role.value}_{uuid.uuid4().hex[:6]}@example.com"
            user = User(
                clerk_user_id=clerk_id,
                email=email,
                full_name=f"Test {role.value}",
                role=role,
            )
            session.add(user)
            roles_users[role] = (clerk_id, email)
        await session.commit()

    # 2. super_admin -> 200
    token_super = create_access_token({"sub": roles_users[UserRole.SUPER_ADMIN][0]})
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/audit-logs", headers={"Authorization": f"Bearer {token_super}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    # 3. admin -> 200
    token_admin = create_access_token({"sub": roles_users[UserRole.ADMIN][0]})
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/audit-logs", headers={"Authorization": f"Bearer {token_admin}"}
        )
        assert resp.status_code == 200

    # 4. researcher -> 403
    token_researcher = create_access_token({"sub": roles_users[UserRole.RESEARCHER][0]})
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/audit-logs", headers={"Authorization": f"Bearer {token_researcher}"}
        )
        assert resp.status_code == 403

    # 5. reviewer -> 403
    token_reviewer = create_access_token({"sub": roles_users[UserRole.REVIEWER][0]})
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/audit-logs", headers={"Authorization": f"Bearer {token_reviewer}"}
        )
        assert resp.status_code == 403

    # 6. contributor -> 403
    token_contrib = create_access_token({"sub": roles_users[UserRole.CONTRIBUTOR][0]})
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/audit-logs", headers={"Authorization": f"Bearer {token_contrib}"}
        )
        assert resp.status_code == 403

    # 7. viewer -> 403
    token_viewer = create_access_token({"sub": roles_users[UserRole.VIEWER][0]})
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/audit-logs", headers={"Authorization": f"Bearer {token_viewer}"}
        )
        assert resp.status_code == 403
