import uuid
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError

from app.db.session import AsyncSessionLocal, engine
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole


@pytest.fixture(autouse=True)
async def clean_engine() -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_user_creation_and_roles() -> None:
    async with AsyncSessionLocal() as session:
        # Create a user with researcher role
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            clerk_user_id=f"user_{uuid.uuid4().hex[:12]}",
            email=f"researcher_{uuid.uuid4().hex[:8]}@example.com",
            full_name="Research Analyst",
            role=UserRole.RESEARCHER,
        )
        session.add(user)
        await session.commit()

        # Query user back
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        saved = result.scalar_one()
        assert saved.email == user.email
        assert saved.role == UserRole.RESEARCHER
        assert saved.is_active is True
        assert saved.created_at is not None


@pytest.mark.asyncio
async def test_audit_log_insert_succeeds() -> None:
    async with AsyncSessionLocal() as session:
        # Create user
        user = User(
            clerk_user_id=f"user_{uuid.uuid4().hex[:12]}",
            email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
            full_name="Admin User",
            role=UserRole.ADMIN,
        )
        session.add(user)
        await session.flush()

        # Insert audit log
        log_id = uuid.uuid4()
        log = AuditLog(
            id=log_id,
            actor_user_id=user.id,
            action="asset.upload",
            resource_type="asset",
            resource_id="asset-101",
            metadata_json={"filename": "press_release.pdf", "size": 2048},
            ip_address="192.168.1.1",
        )
        session.add(log)
        await session.commit()

        # Verify insertion
        stmt = select(AuditLog).where(AuditLog.id == log_id)
        result = await session.execute(stmt)
        saved = result.scalar_one()
        assert saved.action == "asset.upload"
        assert saved.resource_type == "asset"
        assert saved.metadata_json["filename"] == "press_release.pdf"


@pytest.mark.asyncio
async def test_audit_log_immutable_trigger_blocks_update() -> None:
    async with AsyncSessionLocal() as session:
        log_id = uuid.uuid4()
        log = AuditLog(
            id=log_id,
            action="asset.view",
            resource_type="asset",
            resource_id="asset-999",
            metadata_json={"viewed_section": "summary"},
        )
        session.add(log)
        await session.commit()

        # Attempt to update the audit log record
        with pytest.raises(DBAPIError) as exc_info:
            await session.execute(
                update(AuditLog).where(AuditLog.id == log_id).values(action="asset.tampered")
            )
            await session.commit()

        assert "audit_logs entries are immutable" in str(exc_info.value)
        await session.rollback()


@pytest.mark.asyncio
async def test_audit_log_immutable_trigger_blocks_delete() -> None:
    async with AsyncSessionLocal() as session:
        log_id = uuid.uuid4()
        log = AuditLog(
            id=log_id,
            action="asset.download",
            resource_type="asset",
            resource_id="asset-555",
            metadata_json={},
        )
        session.add(log)
        await session.commit()

        # Attempt to delete the audit log record
        with pytest.raises(DBAPIError) as exc_info:
            await session.execute(delete(AuditLog).where(AuditLog.id == log_id))
            await session.commit()

        assert "audit_logs entries are immutable" in str(exc_info.value)
        await session.rollback()
