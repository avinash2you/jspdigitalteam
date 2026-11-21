import uuid
from typing import Any

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.registry import get_ai_provider, get_ocr_provider, get_storage_provider
from app.models.asset import (
    Asset,
    AssetRelationship,
    AssetStatus,
    PrimaryLanguage,
    VerificationStatus,
)
from app.models.document_chunk import DocumentChunk
from app.models.geography import AssetGeoTag, GeoEntity
from app.models.user import User, UserRole
from app.schemas.asset import AssetResponse
from app.schemas.asset_metadata import validate_dynamic_metadata
from app.schemas.extraction import ExtractionResponse, PublishRequest
from app.services.assets import AssetService
from app.services.audit import AuditService


def chunk_text(text: str, max_chunk_chars: int = 1000, overlap: int = 100) -> list[str]:
    """Split text into logical paragraph-aware chunks for pgvector search indexing."""
    if not text or not text.strip():
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return [text.strip()]

    chunks: list[str] = []
    for p in paragraphs:
        if len(p) <= max_chunk_chars:
            chunks.append(p)
        else:
            step = max(1, max_chunk_chars - overlap)
            for i in range(0, len(p), step):
                slice_text = p[i : i + max_chunk_chars].strip()
                if slice_text:
                    chunks.append(slice_text)

    return chunks


class ExtractionService:
    @classmethod
    async def trigger_extraction(
        cls,
        db: AsyncSession,
        asset_id: uuid.UUID,
        user: User,
        client_ip: str | None = None,
    ) -> ExtractionResponse:
        """Fetch asset file, run OCR, run AI (if public), and transition to pending_review."""
        stmt = select(Asset).where(Asset.id == asset_id)
        result = await db.execute(stmt)
        asset = result.scalar_one_or_none()
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset not found",
            )

        if user.role == UserRole.VIEWER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Viewers cannot trigger extraction",
            )

        if user.role == UserRole.CONTRIBUTOR and asset.uploaded_by != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Contributors can only trigger extraction on their own assets",
            )

        # 1. Fetch raw file bytes from StorageProvider
        storage = get_storage_provider()
        try:
            file_bytes = storage.get_object(asset.r2_object_key)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to retrieve asset file from storage: {exc}",
            ) from exc

        # 2. Run OCR via OCRProvider
        ocr = get_ocr_provider()
        langs = (
            ["tel", "eng"]
            if asset.primary_language == PrimaryLanguage.TELUGU
            else ["eng", "tel"]
        )
        try:
            ocr_result = ocr.extract_text(
                file_bytes=file_bytes,
                mime_type=asset.mime_type,
                languages=langs,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OCR extraction failed: {exc}",
            ) from exc

        extracted_text = ocr_result.full_text

        # 3. Run AI extraction ONLY if public_record is True (hard privacy guardrail)
        english_summary = asset.english_summary
        tenglish_keywords = list(asset.tenglish_keywords)
        suggested_meta: dict[str, Any] = {}
        suggested_geo: list[str] = []
        ai_skipped = True
        ai_notice: str | None = None

        if asset.is_public_record:
            ai_skipped = False
            ai_provider = get_ai_provider()
            try:
                ai_result = ai_provider.extract_metadata_and_summary(
                    text_or_bytes=extracted_text,
                    asset_type=asset.asset_type.value,
                    is_public=True,
                )
                english_summary = ai_result.summary
                tenglish_keywords = ai_result.tags
                suggested_meta = ai_result.raw_output.get("suggested_metadata", {})
                suggested_geo = ai_result.raw_output.get("suggested_geo_names", [])

                # Merge AI suggested metadata into existing dynamic metadata
                merged_meta = {**suggested_meta, **asset.dynamic_metadata}
                asset.dynamic_metadata = merged_meta
                asset.english_summary = english_summary
                asset.tenglish_keywords = tenglish_keywords
            except (RuntimeError, ValueError, OSError) as exc:
                ai_notice = f"AI extraction encountered an error: {exc}"
        else:
            ai_notice = (
                "AI extraction skipped for non-public confidential record "
                "to protect data privacy on free-tier."
            )

        # 4. Save extracted draft fields and transition status
        asset.extracted_text = extracted_text
        asset.status = AssetStatus.PENDING_REVIEW
        asset.verification_status = VerificationStatus.PENDING

        await AuditService.record(
            db=db,
            actor_id=user.id,
            action="asset.extract",
            resource_type="asset",
            resource_id=str(asset.id),
            metadata={
                "is_public_record": asset.is_public_record,
                "ai_skipped": ai_skipped,
                "ocr_pages_count": len(ocr_result.pages),
            },
            ip_address=client_ip,
        )

        await db.commit()
        await db.refresh(asset)

        return ExtractionResponse(
            asset_id=asset.id,
            extracted_text=extracted_text,
            english_summary=english_summary,
            tenglish_keywords=tenglish_keywords,
            suggested_metadata=suggested_meta,
            suggested_geo_names=suggested_geo,
            ai_skipped=ai_skipped,
            ai_notice=ai_notice,
            status=asset.status,
        )

    @classmethod
    async def publish_asset(
        cls,
        db: AsyncSession,
        asset_id: uuid.UUID,
        user: User,
        payload: PublishRequest,
        client_ip: str | None = None,
    ) -> AssetResponse:
        """Apply human edits, generate document chunks, transition to published, and record audit log."""
        stmt = (
            select(Asset)
            .where(Asset.id == asset_id)
            .options(
                selectinload(Asset.uploader),
                selectinload(Asset.geo_entities),
                selectinload(Asset.outgoing_relationships).selectinload(
                    AssetRelationship.target_asset
                ),
                selectinload(Asset.incoming_relationships).selectinload(
                    AssetRelationship.source_asset
                ),
            )
        )
        result = await db.execute(stmt)
        asset = result.scalar_one_or_none()
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset not found",
            )

        if user.role == UserRole.VIEWER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Viewers cannot publish assets",
            )

        if user.role == UserRole.CONTRIBUTOR and asset.uploaded_by != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Contributors can only publish their own uploaded assets",
            )

        # 1. Validate approved dynamic metadata
        try:
            validate_dynamic_metadata(asset.asset_type.value, payload.dynamic_metadata)
        except (ValidationError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Dynamic metadata validation failed: {exc}",
            ) from exc

        # 2. Update approved fields
        asset.extracted_text = payload.extracted_text
        asset.english_summary = payload.english_summary
        asset.tenglish_keywords = payload.tenglish_keywords
        asset.dynamic_metadata = payload.dynamic_metadata

        if payload.geo_entity_ids is not None:
            if payload.geo_entity_ids:
                geo_stmt = select(GeoEntity.id).where(GeoEntity.id.in_(payload.geo_entity_ids))
                existing_geo_ids = set((await db.execute(geo_stmt)).scalars().all())
                missing = set(payload.geo_entity_ids) - existing_geo_ids
                if missing:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Geo entities not found: {[str(g) for g in missing]}",
                    )
            await db.execute(delete(AssetGeoTag).where(AssetGeoTag.asset_id == asset.id))
            for gid in set(payload.geo_entity_ids):
                db.add(AssetGeoTag(asset_id=asset.id, geo_entity_id=gid))

        # 3. Generate document chunks
        await db.execute(delete(DocumentChunk).where(DocumentChunk.asset_id == asset.id))
        chunks = chunk_text(payload.extracted_text)
        for idx, text_slice in enumerate(chunks):
            db.add(
                DocumentChunk(
                    asset_id=asset.id,
                    chunk_index=idx,
                    page_number=idx + 1,
                    text=text_slice,
                )
            )

        # 4. Mark published & verified
        asset.status = AssetStatus.PUBLISHED
        asset.verification_status = VerificationStatus.VERIFIED

        # 5. Audit Log (action="asset.edit" per issue technical specification)
        await AuditService.record(
            db=db,
            actor_id=user.id,
            action="asset.edit",
            resource_type="asset",
            resource_id=str(asset.id),
            metadata={
                "action": "publish",
                "chunks_count": len(chunks),
                "status": AssetStatus.PUBLISHED.value,
            },
            ip_address=client_ip,
        )

        await db.commit()
        return await AssetService.get_asset(db=db, asset_id=asset.id, user=user, log_view=False)
