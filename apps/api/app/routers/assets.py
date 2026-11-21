import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.permissions import Permission, require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.asset import (
    AssetCreate,
    AssetResponse,
    AssetUpdate,
    RelationshipCreate,
    RelationshipResponse,
)
from app.services.assets import AssetService

router = APIRouter(prefix="/assets", tags=["Assets"])
require_assets_upload = require_permission(Permission.ASSETS_UPLOAD)


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    payload: AssetCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_assets_upload),
) -> AssetResponse:
    """Create a new asset with validated dynamic metadata, geo tags, and audit logging."""
    client_ip = request.client.host if request.client else None
    return await AssetService.create_asset(
        db=db,
        user=current_user,
        payload=payload,
        client_ip=client_ip,
    )


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetResponse:
    """Retrieve full asset metadata, uploader attribution, geo tags, and bidirectional relationships."""
    client_ip = request.client.host if request.client else None
    return await AssetService.get_asset(
        db=db,
        asset_id=asset_id,
        user=current_user,
        client_ip=client_ip,
        log_view=True,
    )


@router.patch("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: uuid.UUID,
    payload: AssetUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetResponse:
    """Update asset metadata, geo tags, or status with PRD RBAC enforcement and audit logging."""
    client_ip = request.client.host if request.client else None
    return await AssetService.update_asset(
        db=db,
        asset_id=asset_id,
        user=current_user,
        payload=payload,
        client_ip=client_ip,
    )


@router.post(
    "/{asset_id}/relationships",
    response_model=RelationshipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_relationship(
    asset_id: uuid.UUID,
    payload: RelationshipCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RelationshipResponse:
    """Create a relationship (amends/supersedes/clarifies/related) between assets."""
    client_ip = request.client.host if request.client else None
    return await AssetService.add_relationship(
        db=db,
        asset_id=asset_id,
        user=current_user,
        payload=payload,
        client_ip=client_ip,
    )


@router.delete("/{asset_id}/relationships/{rel_id}")
async def delete_relationship(
    asset_id: uuid.UUID,
    rel_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Delete a relationship between assets with audit logging."""
    client_ip = request.client.host if request.client else None
    return await AssetService.delete_relationship(
        db=db,
        asset_id=asset_id,
        rel_id=rel_id,
        user=current_user,
        client_ip=client_ip,
    )


@router.post("/{asset_id}/archive", response_model=AssetResponse)
async def archive_asset(
    asset_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetResponse:
    """Archive an asset with RBAC enforcement and audit logging."""
    client_ip = request.client.host if request.client else None
    return await AssetService.archive_asset(
        db=db,
        asset_id=asset_id,
        user=current_user,
        client_ip=client_ip,
    )
