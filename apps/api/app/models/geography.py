import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.asset import Asset


class GeoTier(str, enum.Enum):
    INDIA = "india"
    STATE = "state"
    DISTRICT = "district"
    PARLIAMENTARY_CONSTITUENCY = "parliamentary_constituency"
    ASSEMBLY_CONSTITUENCY = "assembly_constituency"
    MANDAL = "mandal"
    VILLAGE = "village"
    MUNICIPAL_CORPORATION = "municipal_corporation"
    MUNICIPALITY = "municipality"
    WARD = "ward"


class GeoEntity(Base):
    __tablename__ = "geo_entities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    telugu_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tier: Mapped[GeoTier] = mapped_column(
        Enum(
            GeoTier,
            name="geo_tier",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("geo_entities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    code: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    is_historical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    parent: Mapped["GeoEntity | None"] = relationship(
        "GeoEntity", remote_side=[id], back_populates="children", lazy="selectin"
    )
    children: Mapped[list["GeoEntity"]] = relationship(
        "GeoEntity", back_populates="parent", cascade="all, delete-orphan", lazy="selectin"
    )
    aliases: Mapped[list["GeoAlias"]] = relationship(
        "GeoAlias",
        foreign_keys="GeoAlias.mapped_entity_id",
        back_populates="mapped_entity",
        lazy="selectin",
    )
    assets: Mapped[list["Asset"]] = relationship(
        "Asset", secondary="asset_geo_tags", back_populates="geo_entities", lazy="selectin"
    )


class GeoAlias(Base):
    __tablename__ = "geo_aliases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alias_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    historical_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("geo_entities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    mapped_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("geo_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    valid_until_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    mapped_entity: Mapped["GeoEntity"] = relationship(
        "GeoEntity",
        foreign_keys=[mapped_entity_id],
        back_populates="aliases",
        lazy="selectin",
    )
    historical_entity: Mapped["GeoEntity | None"] = relationship(
        "GeoEntity", foreign_keys=[historical_entity_id]
    )


class AssetGeoTag(Base):
    __tablename__ = "asset_geo_tags"

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        primary_key=True,
    )
    geo_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("geo_entities.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
