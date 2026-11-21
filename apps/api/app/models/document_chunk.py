import uuid
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.asset import Asset


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bbox_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    start_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)

    asset: Mapped["Asset"] = relationship("Asset", back_populates="document_chunks")


Index("ix_document_chunks_asset_chunk", DocumentChunk.asset_id, DocumentChunk.chunk_index)
