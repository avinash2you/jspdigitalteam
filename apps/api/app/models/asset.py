import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.document_chunk import DocumentChunk
    from app.models.geography import GeoEntity
    from app.models.user import User


class AssetType(str, enum.Enum):
    GOVERNMENT_DOCUMENT = "government_document"
    NEWSPAPER_CLIPPING = "newspaper_clipping"
    ONLINE_NEWS_SOCIAL = "online_news_social"
    VIDEO_AUDIO = "video_audio"
    IMAGE_INFOGRAPHIC = "image_infographic"
    RESEARCH_MATERIAL = "research_material"


class PrimaryLanguage(str, enum.Enum):
    TELUGU = "telugu"
    ENGLISH = "english"
    MIXED = "mixed"


class CopyrightFlag(str, enum.Enum):
    PUBLIC_DOMAIN = "public_domain"
    INTERNAL_RESEARCH_ONLY = "internal_research_only"
    RESTRICTED_COPYRIGHT = "restricted_copyright"


class AssetStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    DISPUTED = "disputed"


class RelationType(str, enum.Enum):
    AMENDS = "amends"
    SUPERSEDES = "supersedes"
    CLARIFIES = "clarifies"
    RELATED = "related"


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(
            AssetType,
            name="asset_type",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        index=True,
    )
    primary_language: Mapped[PrimaryLanguage] = mapped_column(
        Enum(
            PrimaryLanguage,
            name="primary_language",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=PrimaryLanguage.TELUGU,
    )
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True, index=True)
    r2_object_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    go_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    copyright_flag: Mapped[CopyrightFlag] = mapped_column(
        Enum(
            CopyrightFlag,
            name="copyright_flag",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=CopyrightFlag.PUBLIC_DOMAIN,
    )
    is_public_record: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    english_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tenglish_keywords: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )
    subject_tags: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )
    dynamic_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default="{}", nullable=False
    )
    status: Mapped[AssetStatus] = mapped_column(
        Enum(
            AssetStatus,
            name="asset_status",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=AssetStatus.DRAFT,
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(
            VerificationStatus,
            name="verification_status",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=VerificationStatus.UNVERIFIED,
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    uploader: Mapped["User | None"] = relationship("User", foreign_keys=[uploaded_by])
    document_chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="asset", cascade="all, delete-orphan"
    )
    outgoing_relationships: Mapped[list["AssetRelationship"]] = relationship(
        "AssetRelationship",
        foreign_keys="AssetRelationship.source_asset_id",
        back_populates="source_asset",
        cascade="all, delete-orphan",
    )
    incoming_relationships: Mapped[list["AssetRelationship"]] = relationship(
        "AssetRelationship",
        foreign_keys="AssetRelationship.target_asset_id",
        back_populates="target_asset",
        cascade="all, delete-orphan",
    )
    geo_entities: Mapped[list["GeoEntity"]] = relationship(
        "GeoEntity", secondary="asset_geo_tags", back_populates="assets", lazy="selectin"
    )


class AssetRelationship(Base):
    __tablename__ = "asset_relationships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_type: Mapped[RelationType] = mapped_column(
        Enum(
            RelationType,
            name="relation_type",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    source_asset: Mapped["Asset"] = relationship(
        "Asset",
        foreign_keys=[source_asset_id],
        back_populates="outgoing_relationships",
    )
    target_asset: Mapped["Asset"] = relationship(
        "Asset",
        foreign_keys=[target_asset_id],
        back_populates="incoming_relationships",
    )
    creator: Mapped["User | None"] = relationship("User", foreign_keys=[created_by])
