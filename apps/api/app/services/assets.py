import uuid
from typing import Any

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.asset import (
    Asset,
    AssetRelationship,
    AssetStatus,
    AssetType,
)
from app.models.geography import AssetGeoTag, GeoEntity
from app.models.user import User, UserRole
from app.schemas.asset import (
    AssetCreate,
    AssetResponse,
    AssetUpdate,
    GeoEntitySummary,
    RelationshipCreate,
    RelationshipResponse,
    RelationshipSummary,
    UploaderSummary,
)
from app.schemas.asset_metadata import validate_dynamic_metadata
from app.services.audit import AuditService


class AssetService:
    @staticmethod
    def _to_asset_response(asset: Asset) -> AssetResponse:
        uploader_summary = None
        if asset.uploader:
            uploader_summary = UploaderSummary(
                id=asset.uploader.id,
                full_name=asset.uploader.full_name,
                email=asset.uploader.email,
                role=asset.uploader.role,
            )

        geo_summaries = [
            GeoEntitySummary(
                id=geo.id,
                name=geo.name,
                telugu_name=geo.telugu_name,
                tier=geo.tier,
                code=geo.code,
            )
            for geo in (asset.geo_entities or [])
        ]

        relationships: list[RelationshipSummary] = []
        for rel in asset.outgoing_relationships or []:
            target = rel.target_asset
            relationships.append(
                RelationshipSummary(
                    id=rel.id,
                    relation_type=rel.relation_type,
                    direction="outgoing",
                    source_asset_id=rel.source_asset_id,
                    target_asset_id=rel.target_asset_id,
                    related_asset_id=rel.target_asset_id,
                    related_asset_title=target.title if target else "",
                    related_asset_type=(
                        target.asset_type if target else AssetType.GOVERNMENT_DOCUMENT
                    ),
                    created_at=rel.created_at,
                )
            )

        for rel in asset.incoming_relationships or []:
            src = rel.source_asset
            relationships.append(
                RelationshipSummary(
                    id=rel.id,
                    relation_type=rel.relation_type,
                    direction="incoming",
                    source_asset_id=rel.source_asset_id,
                    target_asset_id=rel.target_asset_id,
                    related_asset_id=rel.source_asset_id,
                    related_asset_title=src.title if src else "",
                    related_asset_type=src.asset_type if src else AssetType.GOVERNMENT_DOCUMENT,
                    created_at=rel.created_at,
                )
            )

        return AssetResponse(
            id=asset.id,
            title=asset.title,
            asset_type=asset.asset_type,
            primary_language=asset.primary_language,
            source_name=asset.source_name,
            source_url=asset.source_url,
            r2_object_key=asset.r2_object_key,
            file_sha256=asset.file_sha256,
            mime_type=asset.mime_type,
            file_size_bytes=asset.file_size_bytes,
            go_number=asset.go_number,
            copyright_flag=asset.copyright_flag,
            is_public_record=asset.is_public_record,
            extracted_text=asset.extracted_text,
            english_summary=asset.english_summary,
            tenglish_keywords=asset.tenglish_keywords,
            subject_tags=asset.subject_tags,
            dynamic_metadata=asset.dynamic_metadata,
            status=asset.status,
            verification_status=asset.verification_status,
            uploaded_by=asset.uploaded_by,
            uploader=uploader_summary,
            geo_entities=geo_summaries,
            relationships=relationships,
            created_at=asset.created_at,
            updated_at=asset.updated_at,
        )

    @classmethod
    async def create_asset(
        cls,
        db: AsyncSession,
        user: User,
        payload: AssetCreate,
        client_ip: str | None = None,
    ) -> AssetResponse:
        """Create asset with dynamic metadata validation, geo tagging, and audit log."""
        # 1. Validate dynamic metadata against type schema
        try:
            validate_dynamic_metadata(payload.asset_type.value, payload.dynamic_metadata)
        except (ValidationError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Dynamic metadata validation failed: {exc}",
            ) from exc

        # Auto-extract go_number / source_url if present in dynamic_metadata
        go_number = payload.go_number
        if not go_number and "go_number" in payload.dynamic_metadata:
            go_number = str(payload.dynamic_metadata["go_number"])

        source_url = payload.source_url
        if not source_url and "source_url" in payload.dynamic_metadata:
            source_url = str(payload.dynamic_metadata["source_url"])

        # 2. Check geo entities if provided
        if payload.geo_entity_ids:
            geo_stmt = select(GeoEntity.id).where(GeoEntity.id.in_(payload.geo_entity_ids))
            existing_geo_ids = set((await db.execute(geo_stmt)).scalars().all())
            missing_geo_ids = set(payload.geo_entity_ids) - existing_geo_ids
            if missing_geo_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Geo entities not found: {[str(g) for g in missing_geo_ids]}",
                )

        # 3. Create Asset entity
        asset = Asset(
            title=payload.title,
            asset_type=payload.asset_type,
            primary_language=payload.primary_language,
            source_name=payload.source_name,
            source_url=source_url,
            r2_object_key=payload.r2_object_key,
            file_sha256=payload.file_sha256,
            mime_type=payload.mime_type,
            file_size_bytes=payload.file_size_bytes,
            go_number=go_number,
            copyright_flag=payload.copyright_flag,
            is_public_record=payload.is_public_record,
            extracted_text=payload.extracted_text,
            english_summary=payload.english_summary,
            tenglish_keywords=payload.tenglish_keywords,
            subject_tags=payload.subject_tags,
            dynamic_metadata=payload.dynamic_metadata,
            status=payload.status,
            verification_status=payload.verification_status,
            uploaded_by=user.id,
        )
        db.add(asset)
        await db.flush()

        # 4. Attach geo tags
        for geo_id in set(payload.geo_entity_ids):
            db.add(AssetGeoTag(asset_id=asset.id, geo_entity_id=geo_id))

        # 5. Audit Log
        await AuditService.record(
            db=db,
            actor_id=user.id,
            action="asset.upload",
            resource_type="asset",
            resource_id=str(asset.id),
            metadata={
                "title": asset.title,
                "asset_type": asset.asset_type.value,
                "file_sha256": asset.file_sha256,
                "geo_tags_count": len(payload.geo_entity_ids),
            },
            ip_address=client_ip,
        )

        await db.commit()
        return await cls.get_asset(db=db, asset_id=asset.id, user=user, log_view=False)

    @classmethod
    async def get_asset(
        cls,
        db: AsyncSession,
        asset_id: uuid.UUID,
        user: User,
        client_ip: str | None = None,
        log_view: bool = True,
    ) -> AssetResponse:
        """Fetch asset by ID with uploader, geo tags, and bidirectional relationships."""
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

        if log_view:
            await AuditService.record(
                db=db,
                actor_id=user.id,
                action="asset.view",
                resource_type="asset",
                resource_id=str(asset.id),
                metadata={"title": asset.title, "asset_type": asset.asset_type.value},
                ip_address=client_ip,
            )
            await db.commit()

        return cls._to_asset_response(asset)

    @classmethod
    async def update_asset(
        cls,
        db: AsyncSession,
        asset_id: uuid.UUID,
        user: User,
        payload: AssetUpdate,
        client_ip: str | None = None,
    ) -> AssetResponse:
        """Update asset with RBAC enforcement and audit logging."""
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

        # Enforce PRD RBAC
        if user.role == UserRole.VIEWER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Viewers do not have permission to edit assets",
            )

        if user.role == UserRole.CONTRIBUTOR:
            if asset.uploaded_by != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Contributors can only edit their own uploaded assets",
                )
            if asset.status == AssetStatus.PUBLISHED:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Contributors cannot edit published assets",
                )

        if (
            user.role == UserRole.REVIEWER
            and payload.status is not None
            and payload.status not in (AssetStatus.PENDING_REVIEW, AssetStatus.DRAFT)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Reviewers can only edit metadata, not publish or archive assets directly",
            )

        # Dynamic metadata validation if updated
        if payload.dynamic_metadata is not None:
            try:
                validate_dynamic_metadata(asset.asset_type.value, payload.dynamic_metadata)
            except (ValidationError, ValueError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Dynamic metadata validation failed: {exc}",
                ) from exc

        updated_fields: list[str] = []
        payload_data = payload.model_dump(exclude_unset=True)

        if "title" in payload_data and payload_data["title"] is not None:
            asset.title = payload_data["title"]
            updated_fields.append("title")
        if "primary_language" in payload_data and payload_data["primary_language"] is not None:
            asset.primary_language = payload_data["primary_language"]
            updated_fields.append("primary_language")
        if "source_name" in payload_data:
            asset.source_name = payload_data["source_name"]
            updated_fields.append("source_name")
        if "source_url" in payload_data:
            asset.source_url = payload_data["source_url"]
            updated_fields.append("source_url")
        if "go_number" in payload_data:
            asset.go_number = payload_data["go_number"]
            updated_fields.append("go_number")
        if "copyright_flag" in payload_data and payload_data["copyright_flag"] is not None:
            asset.copyright_flag = payload_data["copyright_flag"]
            updated_fields.append("copyright_flag")
        if "is_public_record" in payload_data and payload_data["is_public_record"] is not None:
            asset.is_public_record = payload_data["is_public_record"]
            updated_fields.append("is_public_record")
        if "extracted_text" in payload_data:
            asset.extracted_text = payload_data["extracted_text"]
            updated_fields.append("extracted_text")
        if "english_summary" in payload_data:
            asset.english_summary = payload_data["english_summary"]
            updated_fields.append("english_summary")
        if "tenglish_keywords" in payload_data and payload_data["tenglish_keywords"] is not None:
            asset.tenglish_keywords = payload_data["tenglish_keywords"]
            updated_fields.append("tenglish_keywords")
        if "subject_tags" in payload_data and payload_data["subject_tags"] is not None:
            asset.subject_tags = payload_data["subject_tags"]
            updated_fields.append("subject_tags")
        if "dynamic_metadata" in payload_data and payload_data["dynamic_metadata"] is not None:
            asset.dynamic_metadata = payload_data["dynamic_metadata"]
            updated_fields.append("dynamic_metadata")
        if "status" in payload_data and payload_data["status"] is not None:
            asset.status = payload_data["status"]
            updated_fields.append("status")
        if (
            "verification_status" in payload_data
            and payload_data["verification_status"] is not None
        ):
            asset.verification_status = payload_data["verification_status"]
            updated_fields.append("verification_status")

        if "geo_entity_ids" in payload_data and payload_data["geo_entity_ids"] is not None:
            geo_ids: list[uuid.UUID] = payload_data["geo_entity_ids"]
            if geo_ids:
                geo_stmt = select(GeoEntity.id).where(GeoEntity.id.in_(geo_ids))
                existing_geo_ids = set((await db.execute(geo_stmt)).scalars().all())
                missing_geo_ids = set(geo_ids) - existing_geo_ids
                if missing_geo_ids:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Geo entities not found: {[str(g) for g in missing_geo_ids]}",
                    )
            # Replace geo tags
            await db.execute(delete(AssetGeoTag).where(AssetGeoTag.asset_id == asset.id))
            for gid in set(geo_ids):
                db.add(AssetGeoTag(asset_id=asset.id, geo_entity_id=gid))
            updated_fields.append("geo_entity_ids")

        await AuditService.record(
            db=db,
            actor_id=user.id,
            action="asset.edit",
            resource_type="asset",
            resource_id=str(asset.id),
            metadata={"updated_fields": updated_fields},
            ip_address=client_ip,
        )

        await db.commit()
        return await cls.get_asset(db=db, asset_id=asset.id, user=user, log_view=False)

    @classmethod
    async def add_relationship(
        cls,
        db: AsyncSession,
        asset_id: uuid.UUID,
        user: User,
        payload: RelationshipCreate,
        client_ip: str | None = None,
    ) -> RelationshipResponse:
        """Create a relationship between two assets with RBAC checks and audit logging."""
        if user.role == UserRole.VIEWER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Viewers cannot create asset relationships",
            )

        if asset_id == payload.target_asset_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An asset cannot have a relationship with itself",
            )

        source_asset = await db.scalar(select(Asset).where(Asset.id == asset_id))
        if not source_asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source asset not found",
            )

        target_asset = await db.scalar(select(Asset).where(Asset.id == payload.target_asset_id))
        if not target_asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target asset not found",
            )

        if user.role == UserRole.CONTRIBUTOR:
            if source_asset.uploaded_by != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Contributors can only link their own uploaded assets",
                )
            if source_asset.status == AssetStatus.PUBLISHED:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Contributors cannot link published assets",
                )

        existing_rel = await db.scalar(
            select(AssetRelationship).where(
                AssetRelationship.source_asset_id == asset_id,
                AssetRelationship.target_asset_id == payload.target_asset_id,
                AssetRelationship.relation_type == payload.relation_type,
            )
        )
        if existing_rel:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Relationship already exists between these assets with the same relation type",
            )

        rel = AssetRelationship(
            source_asset_id=asset_id,
            target_asset_id=payload.target_asset_id,
            relation_type=payload.relation_type,
            created_by=user.id,
        )
        db.add(rel)
        await db.flush()

        await AuditService.record(
            db=db,
            actor_id=user.id,
            action="asset.relationship_create",
            resource_type="asset_relationship",
            resource_id=str(rel.id),
            metadata={
                "source_asset_id": str(asset_id),
                "target_asset_id": str(payload.target_asset_id),
                "relation_type": payload.relation_type.value,
            },
            ip_address=client_ip,
        )

        await db.commit()
        await db.refresh(rel)

        return RelationshipResponse(
            id=rel.id,
            source_asset_id=rel.source_asset_id,
            target_asset_id=rel.target_asset_id,
            relation_type=rel.relation_type,
            created_by=rel.created_by,
            created_at=rel.created_at,
        )

    @classmethod
    async def delete_relationship(
        cls,
        db: AsyncSession,
        asset_id: uuid.UUID,
        rel_id: uuid.UUID,
        user: User,
        client_ip: str | None = None,
    ) -> dict[str, Any]:
        """Delete a relationship with RBAC checks and audit logging."""
        if user.role == UserRole.VIEWER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Viewers cannot delete asset relationships",
            )

        rel = await db.scalar(select(AssetRelationship).where(AssetRelationship.id == rel_id))
        if not rel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Relationship not found",
            )

        if rel.source_asset_id != asset_id and rel.target_asset_id != asset_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Relationship does not belong to this asset",
            )

        if user.role == UserRole.CONTRIBUTOR and rel.created_by != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Contributors can only delete relationships they created",
            )

        await AuditService.record(
            db=db,
            actor_id=user.id,
            action="asset.relationship_delete",
            resource_type="asset_relationship",
            resource_id=str(rel.id),
            metadata={"asset_id": str(asset_id), "relationship_id": str(rel_id)},
            ip_address=client_ip,
        )

        await db.delete(rel)
        await db.commit()
        return {"deleted": True, "relationship_id": str(rel_id)}

    @classmethod
    async def archive_asset(
        cls,
        db: AsyncSession,
        asset_id: uuid.UUID,
        user: User,
        client_ip: str | None = None,
    ) -> AssetResponse:
        """Archive an asset (soft-delete) with RBAC checks and audit logging."""
        if user.role == UserRole.VIEWER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Viewers cannot archive assets",
            )

        asset = await db.scalar(select(Asset).where(Asset.id == asset_id))
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset not found",
            )

        if user.role == UserRole.CONTRIBUTOR:
            if asset.uploaded_by != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Contributors can only archive their own uploaded assets",
                )
            if asset.status == AssetStatus.PUBLISHED:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Contributors cannot archive published assets",
                )

        asset.status = AssetStatus.ARCHIVED

        await AuditService.record(
            db=db,
            actor_id=user.id,
            action="asset.archive",
            resource_type="asset",
            resource_id=str(asset.id),
            metadata={"title": asset.title, "status": AssetStatus.ARCHIVED.value},
            ip_address=client_ip,
        )

        await db.commit()
        return await cls.get_asset(db=db, asset_id=asset.id, user=user, log_view=False)
