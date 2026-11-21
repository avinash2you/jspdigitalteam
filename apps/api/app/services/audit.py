import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditService:
    """Service for recording and querying immutable audit logs."""

    @staticmethod
    async def record(
        db: AsyncSession,
        actor_id: uuid.UUID | None,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Persist an append-only audit log entry inside the current transaction."""
        log = AuditLog(
            id=uuid.uuid4(),
            actor_user_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_json=metadata or {},
            ip_address=ip_address,
        )
        db.add(log)
        await db.flush()
        return log

    @staticmethod
    async def list_logs(
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        action: str | None = None,
        resource_type: str | None = None,
        actor_id: uuid.UUID | None = None,
    ) -> tuple[list[AuditLog], int]:
        """Query paginated audit logs with optional filtering."""
        query = select(AuditLog)
        count_query = select(func.count(AuditLog.id))

        if action:
            query = query.where(AuditLog.action == action)
            count_query = count_query.where(AuditLog.action == action)
        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
            count_query = count_query.where(AuditLog.resource_type == resource_type)
        if actor_id:
            query = query.where(AuditLog.actor_user_id == actor_id)
            count_query = count_query.where(AuditLog.actor_user_id == actor_id)

        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        logs = list(result.scalars().all())

        return logs, total
