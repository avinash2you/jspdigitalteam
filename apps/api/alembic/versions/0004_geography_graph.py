"""Create geo_entities, geo_aliases and asset_geo_tags tables.

Revision ID: 0004_geography_graph
Revises: 0003_assets_and_chunks
Create Date: 2026-11-21 17:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_geography_graph"
down_revision: str | None = "0003_assets_and_chunks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create GeoTier Enum
    geo_tier_enum = postgresql.ENUM(
        "india",
        "state",
        "district",
        "parliamentary_constituency",
        "assembly_constituency",
        "mandal",
        "village",
        "municipal_corporation",
        "municipality",
        "ward",
        name="geo_tier",
        create_type=False,
    )
    geo_tier_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create geo_entities table
    op.create_table(
        "geo_entities",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("telugu_name", sa.String(length=255), nullable=True),
        sa.Column("tier", geo_tier_enum, nullable=False),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("geo_entities.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column(
            "is_historical", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_geo_entities_name", "geo_entities", ["name"])
    op.create_index("ix_geo_entities_tier", "geo_entities", ["tier"])
    op.create_index("ix_geo_entities_parent_id", "geo_entities", ["parent_id"])
    op.create_index("ix_geo_entities_code", "geo_entities", ["code"], unique=True)

    # 3. Create geo_aliases table
    op.create_table(
        "geo_aliases",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("alias_name", sa.String(length=255), nullable=False),
        sa.Column(
            "historical_entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("geo_entities.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "mapped_entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("geo_entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("valid_until_year", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_geo_aliases_alias_name", "geo_aliases", ["alias_name"])
    op.create_index(
        "ix_geo_aliases_historical_entity_id", "geo_aliases", ["historical_entity_id"]
    )
    op.create_index("ix_geo_aliases_mapped_entity_id", "geo_aliases", ["mapped_entity_id"])

    # 4. Create asset_geo_tags table
    op.create_table(
        "asset_geo_tags",
        sa.Column(
            "asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "geo_entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("geo_entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("asset_id", "geo_entity_id", name="pk_asset_geo_tags"),
    )
    op.create_index("ix_asset_geo_tags_geo_entity_id", "asset_geo_tags", ["geo_entity_id"])


def downgrade() -> None:
    # 1. Drop tables in reverse order
    op.drop_table("asset_geo_tags")
    op.drop_table("geo_aliases")
    op.drop_table("geo_entities")

    # 2. Drop Enum
    op.execute("DROP TYPE IF EXISTS geo_tier")
