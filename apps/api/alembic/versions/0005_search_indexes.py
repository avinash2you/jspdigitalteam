"""Create search indexes: pg_trgm, GIN FTS and vector indexes.

Revision ID: 0005_search_indexes
Revises: 0004_geography_graph
Create Date: 2026-11-21 19:50:00.000000
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_search_indexes"
down_revision: str | None = "0004_geography_graph"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Enable pg_trgm extension for fuzzy trigram text matching
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # 2. Immutable helper function for array_to_string in index expression
    op.execute("""
        CREATE OR REPLACE FUNCTION immutable_array_to_string(arr text[], sep text)
        RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE AS
        $$ SELECT array_to_string(arr, sep); $$;
    """)

    # 3. Create GIN index on assets for combined full-text search across English, Telugu, and Tenglish
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_assets_fts_simple ON assets USING gin (
            to_tsvector(
                'simple',
                coalesce(title, '') || ' ' ||
                coalesce(extracted_text, '') || ' ' ||
                coalesce(english_summary, '') || ' ' ||
                coalesce(immutable_array_to_string(tenglish_keywords, ' '), '') || ' ' ||
                coalesce(go_number, '')
            )
        );
    """)

    # 4. Create GIN Trigram indexes on assets for fuzzy matching and partial string search
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_assets_title_trgm ON assets USING gin (title gin_trgm_ops);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_assets_go_number_trgm ON assets USING gin (go_number gin_trgm_ops);
    """)

    # 5. Create GIN FTS index and HNSW vector index on document_chunks
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_document_chunks_text_fts ON document_chunks USING gin (
            to_tsvector('simple', text)
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding ON document_chunks USING hnsw (
            embedding vector_cosine_ops
        );
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding;")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_text_fts;")
    op.execute("DROP INDEX IF EXISTS ix_assets_go_number_trgm;")
    op.execute("DROP INDEX IF EXISTS ix_assets_title_trgm;")
    op.execute("DROP INDEX IF EXISTS ix_assets_fts_simple;")
    op.execute("DROP FUNCTION IF EXISTS immutable_array_to_string(text[], text);")
