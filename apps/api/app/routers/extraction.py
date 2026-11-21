import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Permission, require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.asset import AssetResponse
from app.schemas.extraction import ExtractionResponse, PublishRequest
from app.services.extraction import ExtractionService

router = APIRouter(prefix="/assets", tags=["Extraction & Review"])
require_assets_upload = require_permission(Permission.ASSETS_UPLOAD)


@router.post("/{asset_id}/extract", response_model=ExtractionResponse)
async def trigger_extraction(
    asset_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_assets_upload),
) -> ExtractionResponse:
    """Trigger OCR and optional AI metadata extraction on an uploaded asset."""
    client_ip = request.client.host if request.client else None
    return await ExtractionService.trigger_extraction(
        db=db,
        asset_id=asset_id,
        user=current_user,
        client_ip=client_ip,
    )


@router.post("/{asset_id}/publish", response_model=AssetResponse)
async def publish_asset(
    asset_id: uuid.UUID,
    payload: PublishRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_assets_upload),
) -> AssetResponse:
    """Save human-reviewed text and metadata, generate document chunks, and publish the asset."""
    client_ip = request.client.host if request.client else None
    return await ExtractionService.publish_asset(
        db=db,
        asset_id=asset_id,
        user=current_user,
        payload=payload,
        client_ip=client_ip,
    )
