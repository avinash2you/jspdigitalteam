import uuid

from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geography import GeoAlias, GeoEntity, GeoTier


class GeoSearchResultItem(BaseModel):
    id: uuid.UUID
    name: str
    telugu_name: str | None
    tier: str
    code: str | None
    is_historical: bool
    matched_alias: str | None = None


class GeoTreeNode(BaseModel):
    id: uuid.UUID
    name: str
    telugu_name: str | None
    tier: str
    code: str | None


class GeoTreeResponse(BaseModel):
    entity: GeoTreeNode
    ancestors: list[GeoTreeNode]
    children: list[GeoTreeNode]


class GeographyService:
    """Service for searching, expanding, and resolving geographic hierarchy trees."""

    @staticmethod
    async def search_geography(
        db: AsyncSession,
        q: str | None = None,
        tier: str | None = None,
        limit: int = 20,
    ) -> list[GeoSearchResultItem]:
        """Search geography by entity name, Telugu name, or alias name."""
        results: list[GeoSearchResultItem] = []
        seen_ids: set[uuid.UUID] = set()

        tier_enum: GeoTier | None = None
        if tier:
            try:
                tier_enum = GeoTier(tier.lower())
            except ValueError:
                return []

        # 1. Search direct matches on GeoEntity name or telugu_name
        stmt = select(GeoEntity)
        if tier_enum is not None:
            stmt = stmt.where(GeoEntity.tier == tier_enum)

        if q and q.strip():
            query_str = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    GeoEntity.name.ilike(query_str),
                    GeoEntity.telugu_name.ilike(query_str),
                    GeoEntity.code.ilike(query_str),
                )
            )

        stmt = stmt.limit(limit)
        direct_matches = (await db.execute(stmt)).scalars().all()

        for entity in direct_matches:
            seen_ids.add(entity.id)
            results.append(
                GeoSearchResultItem(
                    id=entity.id,
                    name=entity.name,
                    telugu_name=entity.telugu_name,
                    tier=entity.tier.value,
                    code=entity.code,
                    is_historical=entity.is_historical,
                    matched_alias=None,
                )
            )

        # 2. Search matches through GeoAliases if remaining limit allows
        remaining_limit = limit - len(results)
        if remaining_limit > 0 and q and q.strip():
            query_str = f"%{q.strip()}%"
            alias_stmt = (
                select(GeoAlias, GeoEntity)
                .join(GeoEntity, GeoAlias.mapped_entity_id == GeoEntity.id)
                .where(GeoAlias.alias_name.ilike(query_str))
            )
            if tier_enum is not None:
                alias_stmt = alias_stmt.where(GeoEntity.tier == tier_enum)

            alias_stmt = alias_stmt.limit(remaining_limit)
            alias_rows = (await db.execute(alias_stmt)).all()

            for alias, entity in alias_rows:
                if entity.id not in seen_ids:
                    seen_ids.add(entity.id)
                    results.append(
                        GeoSearchResultItem(
                            id=entity.id,
                            name=entity.name,
                            telugu_name=entity.telugu_name,
                            tier=entity.tier.value,
                            code=entity.code,
                            is_historical=entity.is_historical,
                            matched_alias=alias.alias_name,
                        )
                    )

        return results

    @staticmethod
    async def resolve_geo_filter_ids(
        db: AsyncSession,
        geo_ids: list[uuid.UUID],
    ) -> set[uuid.UUID]:
        """Expand selected geo IDs to include all hierarchical descendants and pre-2022 alias entities."""
        if not geo_ids:
            return set()

        # 1. Recursive CTE finding all child descendants of the target geo IDs
        base_query = select(GeoEntity.id).where(GeoEntity.id.in_(geo_ids))
        cte = base_query.cte(name="descendants", recursive=True)
        joined_query = select(GeoEntity.id).join(cte, GeoEntity.parent_id == cte.c.id)
        recursive_cte = cte.union_all(joined_query)

        res = await db.execute(select(recursive_cte.c.id))
        expanded_ids: set[uuid.UUID] = set(res.scalars().all())

        # 2. Resolve linked pre-2022 historical aliases
        alias_stmt = select(GeoAlias.alias_name).where(
            GeoAlias.mapped_entity_id.in_(expanded_ids)
        )
        alias_names = (await db.execute(alias_stmt)).scalars().all()

        if alias_names:
            linked_stmt = select(
                GeoAlias.mapped_entity_id, GeoAlias.historical_entity_id
            ).where(GeoAlias.alias_name.in_(alias_names))
            linked_rows = (await db.execute(linked_stmt)).all()
            for mapped_id, hist_id in linked_rows:
                if mapped_id is not None:
                    expanded_ids.add(mapped_id)
                if hist_id is not None:
                    expanded_ids.add(hist_id)

        return expanded_ids

    @staticmethod
    async def get_geo_tree(
        db: AsyncSession,
        entity_id: uuid.UUID,
    ) -> GeoTreeResponse | None:
        """Fetch targeted geographic entity with its complete ancestor chain and immediate children."""
        stmt = select(GeoEntity).where(GeoEntity.id == entity_id)
        entity = (await db.execute(stmt)).scalar_one_or_none()
        if entity is None:
            return None

        # Fetch immediate children
        child_stmt = (
            select(GeoEntity)
            .where(GeoEntity.parent_id == entity_id)
            .order_by(GeoEntity.name)
        )
        children = (await db.execute(child_stmt)).scalars().all()

        # Fetch ancestors using iterative parent navigation
        ancestors: list[GeoTreeNode] = []
        curr_parent_id = entity.parent_id
        while curr_parent_id is not None:
            p_stmt = select(GeoEntity).where(GeoEntity.id == curr_parent_id)
            parent = (await db.execute(p_stmt)).scalar_one_or_none()
            if parent is None:
                break
            ancestors.append(
                GeoTreeNode(
                    id=parent.id,
                    name=parent.name,
                    telugu_name=parent.telugu_name,
                    tier=parent.tier.value,
                    code=parent.code,
                )
            )
            curr_parent_id = parent.parent_id

        # Reverse so root (e.g. India) comes first
        ancestors.reverse()

        return GeoTreeResponse(
            entity=GeoTreeNode(
                id=entity.id,
                name=entity.name,
                telugu_name=entity.telugu_name,
                tier=entity.tier.value,
                code=entity.code,
            ),
            ancestors=ancestors,
            children=[
                GeoTreeNode(
                    id=c.id,
                    name=c.name,
                    telugu_name=c.telugu_name,
                    tier=c.tier.value,
                    code=c.code,
                )
                for c in children
            ],
        )
