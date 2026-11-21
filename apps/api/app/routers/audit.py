import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Permission, require_permission
from app.db.session import get_db
from app.models.user import User
from app.services.audit import AuditService

router = APIRouter(prefix="/audit-logs", tags=["audit"])

audit_view_guard = require_permission(Permission.AUDIT_VIEW)


class AuditLogItem(BaseModel):
    id: str
    actor_user_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    metadata_json: dict[str, Any]
    ip_address: str | None
    created_at: str


class AuditLogListResponse(BaseModel):
    total: int
    items: list[AuditLogItem]
    limit: int
    offset: int


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    action: str | None = None,
    resource_type: str | None = None,
    actor_id: uuid.UUID | None = None,
    current_user: User = Depends(audit_view_guard),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List audit logs with pagination and optional filtering. Gated by audit:view."""
    logs, total = await AuditService.list_logs(
        db=db,
        limit=limit,
        offset=offset,
        action=action,
        resource_type=resource_type,
        actor_id=actor_id,
    )
    return {
        "total": total,
        "items": [
            {
                "id": str(log.id),
                "actor_user_id": str(log.actor_user_id) if log.actor_user_id else None,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "metadata_json": log.metadata_json,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
        "limit": limit,
        "offset": offset,
    }
