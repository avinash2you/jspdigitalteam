import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.asset import (
    AssetStatus,
    AssetType,
    CopyrightFlag,
    PrimaryLanguage,
    RelationType,
    VerificationStatus,
)
from app.models.geography import GeoTier
from app.models.user import UserRole


class GeoEntitySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    telugu_name: str | None = None
    tier: GeoTier
    code: str | None = None


class UploaderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str | None = None
    email: str
    role: UserRole


class RelationshipSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    relation_type: RelationType
    direction: str  # "outgoing" | "incoming"
    source_asset_id: uuid.UUID
    target_asset_id: uuid.UUID
    related_asset_id: uuid.UUID
    related_asset_title: str
    related_asset_type: AssetType
    created_at: datetime


class AssetCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    asset_type: AssetType
    primary_language: PrimaryLanguage = PrimaryLanguage.TELUGU
    source_name: str | None = None
    source_url: str | None = None
    r2_object_key: str = Field(min_length=1)
    file_sha256: str = Field(min_length=64, max_length=64)
    mime_type: str = Field(min_length=1)
    file_size_bytes: int = Field(gt=0)
    go_number: str | None = None
    copyright_flag: CopyrightFlag = CopyrightFlag.PUBLIC_DOMAIN
    is_public_record: bool = False
    extracted_text: str | None = None
    english_summary: str | None = None
    tenglish_keywords: list[str] = Field(default_factory=list)
    subject_tags: list[str] = Field(default_factory=list)
    dynamic_metadata: dict[str, Any] = Field(default_factory=dict)
    geo_entity_ids: list[uuid.UUID] = Field(default_factory=list)
    status: AssetStatus = AssetStatus.DRAFT
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED


class AssetUpdate(BaseModel):
    title: str | None = None
    primary_language: PrimaryLanguage | None = None
    source_name: str | None = None
    source_url: str | None = None
    go_number: str | None = None
    copyright_flag: CopyrightFlag | None = None
    is_public_record: bool | None = None
    extracted_text: str | None = None
    english_summary: str | None = None
    tenglish_keywords: list[str] | None = None
    subject_tags: list[str] | None = None
    dynamic_metadata: dict[str, Any] | None = None
    geo_entity_ids: list[uuid.UUID] | None = None
    status: AssetStatus | None = None
    verification_status: VerificationStatus | None = None


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    asset_type: AssetType
    primary_language: PrimaryLanguage
    source_name: str | None = None
    source_url: str | None = None
    r2_object_key: str
    file_sha256: str
    mime_type: str
    file_size_bytes: int
    go_number: str | None = None
    copyright_flag: CopyrightFlag
    is_public_record: bool
    extracted_text: str | None = None
    english_summary: str | None = None
    tenglish_keywords: list[str]
    subject_tags: list[str]
    dynamic_metadata: dict[str, Any]
    status: AssetStatus
    verification_status: VerificationStatus
    uploaded_by: uuid.UUID | None = None
    uploader: UploaderSummary | None = None
    geo_entities: list[GeoEntitySummary] = Field(default_factory=list)
    relationships: list[RelationshipSummary] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class RelationshipCreate(BaseModel):
    target_asset_id: uuid.UUID
    relation_type: RelationType


class RelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_asset_id: uuid.UUID
    target_asset_id: uuid.UUID
    relation_type: RelationType
    created_by: uuid.UUID | None = None
    created_at: datetime
