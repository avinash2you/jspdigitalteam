import asyncio
import concurrent.futures
import re
import uuid
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool

from app.adapters.base import (
    AssetSearchDocument,
    SearchFilters,
    SearchResponse,
    SearchResultItem,
)
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.asset import Asset, AssetStatus, AssetType
from app.models.document_chunk import DocumentChunk
from app.models.geography import AssetGeoTag
from app.services.geography import GeographyService

T = TypeVar("T")


def _run_in_isolated_thread(
    coro_fn: Callable[[AsyncSession], Coroutine[Any, Any, T]],
) -> T:
    """Run an async database operation in an isolated thread with its own connection loop."""
    def _worker() -> T:
        async def _exec() -> T:
            eng = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
            session_factory = async_sessionmaker(
                eng, class_=AsyncSession, expire_on_commit=False
            )
            try:
                async with session_factory() as session:
                    res = await coro_fn(session)
                    await session.commit()
                    return res
            finally:
                await eng.dispose()

        return asyncio.run(_exec())

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_worker).result()


class PostgresHybridSearchProvider:
    """Postgres full-text + trigram + pgvector hybrid search provider with RRF ranking."""

    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession] | None = None
    ) -> None:
        self.session_factory = session_factory or AsyncSessionLocal

    # =========================================================================
    # Synchronous Protocol Methods
    # =========================================================================

    def index_asset(self, asset_doc: AssetSearchDocument) -> None:
        """Synchronously index or update an asset document into Postgres."""
        _run_in_isolated_thread(lambda session: self.aindex_asset(asset_doc, session=session))

    def delete_asset(self, asset_id: str) -> None:
        """Synchronously delete an asset document from Postgres."""
        _run_in_isolated_thread(lambda session: self.adelete_asset(asset_id, session=session))

    def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> SearchResponse:
        """Synchronously search across assets using hybrid ranking."""
        return _run_in_isolated_thread(
            lambda session: self.asearch(query, filters, limit, offset, session=session)
        )

    # =========================================================================
    # Async Methods (High-performance native async)
    # =========================================================================

    async def aindex_asset(
        self, asset_doc: AssetSearchDocument, session: AsyncSession | None = None
    ) -> None:
        """Index or update an asset in the database."""
        if session is not None:
            await self._execute_index(session, asset_doc)
        else:
            async with self.session_factory() as local_session:
                await self._execute_index(local_session, asset_doc)
                await local_session.commit()

    async def _execute_index(
        self, session: AsyncSession, asset_doc: AssetSearchDocument
    ) -> None:
        try:
            asset_uuid = uuid.UUID(asset_doc.id)
        except ValueError:
            asset_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, asset_doc.id)

        stmt = select(Asset).where(Asset.id == asset_uuid)
        existing = (await session.execute(stmt)).scalar_one_or_none()

        if existing:
            existing.title = asset_doc.title
            if asset_doc.content_text:
                existing.extracted_text = asset_doc.content_text
            if asset_doc.description:
                existing.english_summary = asset_doc.description
            if asset_doc.tags:
                existing.subject_tags = list(set(existing.subject_tags + asset_doc.tags))
            if asset_doc.metadata:
                existing.dynamic_metadata = {
                    **existing.dynamic_metadata,
                    **asset_doc.metadata,
                }
        else:
            # Create a published asset record for search indexing
            new_asset = Asset(
                id=asset_uuid,
                title=asset_doc.title,
                asset_type=AssetType(asset_doc.asset_type)
                if asset_doc.asset_type in [e.value for e in AssetType]
                else AssetType.GOVERNMENT_DOCUMENT,
                r2_object_key=f"search-indexed/{asset_uuid}",
                file_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
                mime_type="text/plain",
                file_size_bytes=len(asset_doc.content_text or ""),
                status=AssetStatus.PUBLISHED,
                extracted_text=asset_doc.content_text,
                english_summary=asset_doc.description,
                subject_tags=asset_doc.tags,
                dynamic_metadata=asset_doc.metadata,
            )
            session.add(new_asset)

    async def adelete_asset(
        self, asset_id: str, session: AsyncSession | None = None
    ) -> None:
        """Delete an asset from the database."""
        try:
            asset_uuid = uuid.UUID(asset_id)
        except ValueError:
            asset_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, asset_id)

        if session is not None:
            await self._execute_delete(session, asset_uuid)
        else:
            async with self.session_factory() as local_session:
                await self._execute_delete(local_session, asset_uuid)
                await local_session.commit()

    async def _execute_delete(self, session: AsyncSession, asset_uuid: uuid.UUID) -> None:
        stmt = select(Asset).where(Asset.id == asset_uuid)
        asset = (await session.execute(stmt)).scalar_one_or_none()
        if asset:
            await session.delete(asset)

    async def asearch(
        self,
        query: str,
        filters: SearchFilters | None = None,
        limit: int = 20,
        offset: int = 0,
        session: AsyncSession | None = None,
        query_embedding: list[float] | None = None,
    ) -> SearchResponse:
        """Execute hybrid search combining FTS, trigram, exact GO match, and pgvector semantic similarity."""
        if session is not None:
            return await self._execute_search(
                session, query, filters, limit, offset, query_embedding
            )
        else:
            async with self.session_factory() as local_session:
                return await self._execute_search(
                    local_session, query, filters, limit, offset, query_embedding
                )

    async def _execute_search(
        self,
        session: AsyncSession,
        query: str,
        filters: SearchFilters | None,
        limit: int,
        offset: int,
        query_embedding: list[float] | None,
    ) -> SearchResponse:
        q = (query or "").strip()
        where_clauses: list[Any] = [Asset.status == AssetStatus.PUBLISHED]

        # ---------------------------------------------------------------------
        # 1. Relational Filters
        # ---------------------------------------------------------------------
        if filters:
            # Asset type filters
            if filters.asset_type:
                where_clauses.append(Asset.asset_type == filters.asset_type)
            elif filters.asset_types:
                where_clauses.append(Asset.asset_type.in_(filters.asset_types))

            # Date range filters evaluated against effective publication date
            pub_date_expr = func.coalesce(
                Asset.dynamic_metadata["publication_date"].as_string(),
                Asset.dynamic_metadata["date_of_issue"].as_string(),
                Asset.dynamic_metadata["published_date"].as_string(),
                func.to_char(Asset.created_at, "YYYY-MM-DD"),
            )

            date_from = filters.date_from or filters.start_date
            if date_from:
                where_clauses.append(pub_date_expr >= date_from)

            date_to = filters.date_to or filters.end_date
            if date_to:
                where_clauses.append(pub_date_expr <= date_to)

            # Department filter
            if filters.department:
                where_clauses.append(
                    Asset.dynamic_metadata["issuing_department"].as_string().ilike(
                        f"%{filters.department}%"
                    )
                )

            # Geography filter with alias & descendant expansion
            if filters.geo_ids:
                expanded_geo_ids = await GeographyService.resolve_geo_filter_ids(
                    session, filters.geo_ids
                )
                if not expanded_geo_ids:
                    return SearchResponse(total=0, items=[], limit=limit, offset=offset)
                where_clauses.append(
                    Asset.id.in_(
                        select(AssetGeoTag.asset_id).where(
                            AssetGeoTag.geo_entity_id.in_(expanded_geo_ids)
                        )
                    )
                )

            # Verification status filter
            if filters.verification_status:
                where_clauses.append(Asset.verification_status == filters.verification_status)

            # Subject / Tenglish tags filter
            if filters.tags:
                where_clauses.append(
                    or_(
                        Asset.subject_tags.overlap(filters.tags),
                        Asset.tenglish_keywords.overlap(filters.tags),
                    )
                )

        # ---------------------------------------------------------------------
        # 2. Text / Lexical Matching & Ranking Expressions
        # ---------------------------------------------------------------------
        if q:
            fts_doc = func.to_tsvector(
                "simple",
                func.coalesce(Asset.title, "")
                + " "
                + func.coalesce(Asset.extracted_text, "")
                + " "
                + func.coalesce(Asset.english_summary, "")
                + " "
                + func.coalesce(func.immutable_array_to_string(Asset.tenglish_keywords, " "), "")
                + " "
                + func.coalesce(Asset.go_number, ""),
            )
            ts_query = func.plainto_tsquery("simple", q)
            fts_match = fts_doc.op("@@")(ts_query)
            fts_rank = func.ts_rank_cd(fts_doc, ts_query)

            exact_go_match = Asset.go_number.ilike(f"%{q}%")
            title_ilike = Asset.title.ilike(f"%{q}%")
            text_ilike = Asset.extracted_text.ilike(f"%{q}%")
            tenglish_kw_match = func.immutable_array_to_string(
                Asset.tenglish_keywords, " "
            ).ilike(f"%{q}%")
            title_trgm_sim = func.similarity(Asset.title, q)

            lexical_where = or_(
                fts_match,
                exact_go_match,
                title_ilike,
                text_ilike,
                tenglish_kw_match,
                title_trgm_sim > 0.2,
            )
            where_clauses.append(lexical_where)

            lexical_score_expr = (
                case((exact_go_match, 10.0), else_=0.0)
                + case((fts_match, fts_rank * 5.0), else_=0.0)
                + case((title_ilike, 3.0), else_=0.0)
                + case((tenglish_kw_match, 3.0), else_=0.0)
                + case((text_ilike, 1.5), else_=0.0)
                + func.coalesce(title_trgm_sim, 0.0)
            ).label("lexical_score")

            headline_expr = func.ts_headline(
                "simple",
                func.coalesce(Asset.extracted_text, Asset.english_summary, Asset.title),
                ts_query,
                "StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15",
            ).label("highlighted_snippet")
        else:
            lexical_score_expr = func.coalesce(1.0).label("lexical_score")
            headline_expr = func.coalesce(
                Asset.english_summary, Asset.extracted_text, Asset.title
            ).label("highlighted_snippet")

        # ---------------------------------------------------------------------
        # 3. Execute Lexical Query Candidates
        # ---------------------------------------------------------------------
        count_stmt = select(func.count(Asset.id)).where(*where_clauses)
        total_matching = (await session.scalar(count_stmt)) or 0

        # Retrieve candidates for RRF or direct pagination
        candidate_limit = max(limit + offset, 100) if query_embedding else limit
        candidate_offset = 0 if query_embedding else offset

        lex_stmt = (
            select(Asset, lexical_score_expr, headline_expr)
            .where(*where_clauses)
            .options(selectinload(Asset.geo_entities))
            .order_by(lexical_score_expr.desc(), Asset.created_at.desc())
            .offset(candidate_offset)
            .limit(candidate_limit)
        )
        lex_rows = (await session.execute(lex_stmt)).all()

        # ---------------------------------------------------------------------
        # 4. Vector Semantic Search & Reciprocal Rank Fusion (RRF)
        # ---------------------------------------------------------------------
        if query_embedding and lex_rows:
            # Query vector distances on document chunks
            matched_asset_ids = [row[0].id for row in lex_rows]
            vec_stmt = (
                select(
                    DocumentChunk.asset_id,
                    func.min(DocumentChunk.embedding.cosine_distance(query_embedding)).label(
                        "min_distance"
                    ),
                )
                .where(
                    and_(
                        DocumentChunk.asset_id.in_(matched_asset_ids),
                        DocumentChunk.embedding.isnot(None),
                    )
                )
                .group_by(DocumentChunk.asset_id)
                .order_by("min_distance")
            )
            vec_rows = (await session.execute(vec_stmt)).all()
            vec_rank_map = {row[0]: idx + 1 for idx, row in enumerate(vec_rows)}

            # Combine using RRF: score = 1/(60 + lex_rank) + 1/(60 + vec_rank)
            rrf_candidates: list[tuple[float, Any, str]] = []
            for idx, (asset, _l_score, snippet) in enumerate(lex_rows):
                lex_rank = idx + 1
                vec_rank = vec_rank_map.get(asset.id, 1000)
                rrf_score = (1.0 / (60.0 + lex_rank)) + (1.0 / (60.0 + vec_rank))
                rrf_candidates.append((rrf_score, asset, snippet))

            rrf_candidates.sort(key=lambda x: x[0], reverse=True)
            paginated_candidates = rrf_candidates[offset : offset + limit]
            final_items = [
                self._build_search_result_item(asset, rrf_score, snippet, q)
                for rrf_score, asset, snippet in paginated_candidates
            ]
        else:
            final_items = [
                self._build_search_result_item(asset, float(score), snippet, q)
                for asset, score, snippet in lex_rows
            ]

        return SearchResponse(
            total=total_matching,
            items=final_items,
            limit=limit,
            offset=offset,
        )

    def _build_search_result_item(
        self, asset: Asset, score: float, highlighted: str, query: str
    ) -> SearchResultItem:
        meta = asset.dynamic_metadata or {}
        headline = meta.get("headline") or asset.title
        pub_date = (
            meta.get("publication_date")
            or meta.get("date_of_issue")
            or meta.get("published_date")
            or (asset.created_at.strftime("%Y-%m-%d") if asset.created_at else None)
        )

        # Highlight query keywords with <mark> if ts_headline did not produce marks
        snippet = highlighted or asset.english_summary or asset.extracted_text or asset.title
        if query and "<mark>" not in snippet:
            for term in query.split():
                if len(term) >= 2:
                    pattern = re.compile(re.escape(term), re.IGNORECASE)
                    snippet = pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", snippet)

        geo_summaries = [
            {
                "id": str(g.id),
                "name": g.name,
                "telugu_name": g.telugu_name,
                "tier": str(g.tier.value if hasattr(g.tier, "value") else g.tier),
                "code": g.code,
            }
            for g in (asset.geo_entities or [])
        ]

        from app.adapters.registry import get_storage_provider

        storage = get_storage_provider()
        preview_url = (
            storage.generate_download_url(asset.r2_object_key, expires_sec=300)
            if asset.r2_object_key
            else None
        )

        return SearchResultItem(
            id=str(asset.id),
            title=asset.title,
            snippet=snippet,
            score=round(score, 4),
            asset_type=str(asset.asset_type.value if hasattr(asset.asset_type, "value") else asset.asset_type),
            headline=str(headline) if headline else None,
            highlighted_snippet=snippet,
            go_number=asset.go_number,
            publication_date=str(pub_date) if pub_date else None,
            source_name=asset.source_name or meta.get("newspaper_name") or meta.get("platform_publisher"),
            preview_url=preview_url,
            geo_tags=geo_summaries,
        )
