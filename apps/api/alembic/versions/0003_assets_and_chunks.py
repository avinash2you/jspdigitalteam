"""Create assets, asset_relationships and document_chunks tables.

Revision ID: 0003_assets_and_chunks
Revises: 0002_users_and_audit_logs
Create Date: 2026-11-21 17:15:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_assets_and_chunks"
down_revision: str | None = "0002_users_and_audit_logs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create Enums
    asset_type_enum = postgresql.ENUM(
        "government_document",
        "newspaper_clipping",
        "online_news_social",
        "video_audio",
        "image_infographic",
        "research_material",
        name="asset_type",
        create_type=False,
    )
    asset_type_enum.create(op.get_bind(), checkfirst=True)

    primary_language_enum = postgresql.ENUM(
        "telugu",
        "english",
        "mixed",
        name="primary_language",
        create_type=False,
    )
    primary_language_enum.create(op.get_bind(), checkfirst=True)

    copyright_flag_enum = postgresql.ENUM(
        "public_domain",
        "internal_research_only",
        "restricted_copyright",
        name="copyright_flag",
        create_type=False,
    )
    copyright_flag_enum.create(op.get_bind(), checkfirst=True)

    asset_status_enum = postgresql.ENUM(
        "draft",
        "pending_review",
        "published",
        "archived",
        name="asset_status",
        create_type=False,
    )
    asset_status_enum.create(op.get_bind(), checkfirst=True)

    verification_status_enum = postgresql.ENUM(
        "unverified",
        "pending",
        "verified",
        "disputed",
        name="verification_status",
        create_type=False,
    )
    verification_status_enum.create(op.get_bind(), checkfirst=True)

    relation_type_enum = postgresql.ENUM(
        "amends",
        "supersedes",
        "clarifies",
        "related",
        name="relation_type",
        create_type=False,
    )
    relation_type_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create assets table
    op.create_table(
        "assets",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("asset_type", asset_type_enum, nullable=False),
        sa.Column(
            "primary_language", primary_language_enum, nullable=False, server_default="telugu"
        ),
        sa.Column("source_name", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("r2_object_key", sa.String(length=1024), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("go_number", sa.String(length=100), nullable=True),
        sa.Column(
            "copyright_flag", copyright_flag_enum, nullable=False, server_default="public_domain"
        ),
        sa.Column(
            "is_public_record", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("english_summary", sa.Text(), nullable=True),
        sa.Column(
            "tenglish_keywords",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "subject_tags",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "dynamic_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("status", asset_status_enum, nullable=False, server_default="draft"),
        sa.Column(
            "verification_status",
            verification_status_enum,
            nullable=False,
            server_default="unverified",
        ),
        sa.Column(
            "uploaded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_assets_asset_type", "assets", ["asset_type"])
    op.create_index("ix_assets_file_sha256", "assets", ["file_sha256"])
    op.create_index("ix_assets_go_number", "assets", ["go_number"])
    op.create_index("ix_assets_source_url", "assets", ["source_url"])
    op.create_index("ix_assets_uploaded_by", "assets", ["uploaded_by"])

    # 3. Create asset_relationships table
    op.create_table(
        "asset_relationships",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "source_asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relation_type", relation_type_enum, nullable=False),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_asset_relationships_source_asset_id", "asset_relationships", ["source_asset_id"]
    )
    op.create_index(
        "ix_asset_relationships_target_asset_id", "asset_relationships", ["target_asset_id"]
    )

    # 4. Create document_chunks table
    op.create_table(
        "document_chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("bbox_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("start_sec", sa.Float(), nullable=True),
        sa.Column("end_sec", sa.Float(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=True),
    )
    op.create_index("ix_document_chunks_asset_id", "document_chunks", ["asset_id"])
    op.create_index(
        "ix_document_chunks_asset_chunk", "document_chunks", ["asset_id", "chunk_index"]
    )


def downgrade() -> None:
    # 1. Drop tables in reverse order
    op.drop_table("document_chunks")
    op.drop_table("asset_relationships")
    op.drop_table("assets")

    # 2. Drop Enums
    op.execute("DROP TYPE IF EXISTS relation_type")
    op.execute("DROP TYPE IF EXISTS verification_status")
    op.execute("DROP TYPE IF EXISTS asset_status")
    op.execute("DROP TYPE IF EXISTS copyright_flag")
    op.execute("DROP TYPE IF EXISTS primary_language")
    op.execute("DROP TYPE IF EXISTS asset_type")
