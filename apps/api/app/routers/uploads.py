import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.registry import get_storage_provider
from app.core.auth import get_current_user
from app.core.permissions import Permission, require_permission
from app.db.session import get_db
from app.models.asset import Asset
from app.models.user import User
from app.services.audit import AuditService
from app.services.dedup import DeduplicationService, DuplicateMatch

router = APIRouter(tags=["Uploads & Downloads"])

MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB limit for Stage 0 pilot
require_assets_upload = require_permission(Permission.ASSETS_UPLOAD)


class CheckDuplicateRequest(BaseModel):
    file_sha256: str | None = None
    go_number: str | None = None
    source_url: str | None = None


class CheckDuplicateResponse(BaseModel):
    is_duplicate: bool
    matches: list[DuplicateMatch]


class PresignedUploadRequest(BaseModel):
    filename: str
    mime_type: str
    file_size_bytes: int


class PresignedUploadResponse(BaseModel):
    object_key: str
    upload_url: str
    expires_in: int


class DownloadUrlResponse(BaseModel):
    asset_id: str
    download_url: str
    expires_in: int


def _sanitize_filename(filename: str) -> str:
    base = Path(filename).name
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]", "_", base)
    return cleaned or "file.bin"


@router.post("/uploads/check-duplicate", response_model=CheckDuplicateResponse)
async def check_duplicate_assets(
    payload: CheckDuplicateRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_assets_upload),
) -> CheckDuplicateResponse:
    """Check for duplicate assets by SHA-256 checksum, normalized GO number, or source URL."""
    matches = await DeduplicationService.check_duplicates(
        db=db,
        file_sha256=payload.file_sha256,
        go_number=payload.go_number,
        source_url=payload.source_url,
    )
    return CheckDuplicateResponse(is_duplicate=len(matches) > 0, matches=matches)


@router.post("/uploads/presign", response_model=PresignedUploadResponse)
async def create_presigned_upload_url(
    payload: PresignedUploadRequest,
    _user: User = Depends(require_assets_upload),
) -> PresignedUploadResponse:
    """Issue a short-lived presigned PUT URL for Cloudflare R2 direct upload."""
    if payload.file_size_bytes <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must be greater than 0 bytes",
        )
    if payload.file_size_bytes > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds maximum allowed limit of 50MB",
        )
    if not payload.mime_type or "/" not in payload.mime_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid MIME type is required",
        )

    now = datetime.now(UTC)
    safe_name = _sanitize_filename(payload.filename)
    object_key = f"raw/{now.strftime('%Y/%m')}/{uuid.uuid4().hex}_{safe_name}"

    storage_provider = get_storage_provider()
    upload_url = storage_provider.generate_upload_url(
        key=object_key,
        content_type=payload.mime_type,
        expires_sec=300,
    )

    return PresignedUploadResponse(
        object_key=object_key,
        upload_url=upload_url,
        expires_in=300,
    )


@router.get("/assets/{asset_id}/download-url", response_model=DownloadUrlResponse)
async def get_asset_download_url(
    asset_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DownloadUrlResponse:
    """Generate a short-lived presigned GET URL for an asset and record an audit log."""
    stmt = select(Asset).where(Asset.id == asset_id)
    result = await db.execute(stmt)
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    storage_provider = get_storage_provider()
    download_url = storage_provider.generate_download_url(
        key=asset.r2_object_key,
        expires_sec=300,
    )

    client_ip = request.client.host if request.client else None
    await AuditService.record(
        db=db,
        actor_id=current_user.id,
        action="asset.download",
        resource_type="asset",
        resource_id=str(asset.id),
        metadata={"title": asset.title, "mime_type": asset.mime_type},
        ip_address=client_ip,
    )
    await db.commit()

    return DownloadUrlResponse(
        asset_id=str(asset.id),
        download_url=download_url,
        expires_in=300,
    )
