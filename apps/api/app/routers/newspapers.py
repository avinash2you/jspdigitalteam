import math
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.registry import get_storage_provider
from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.asset import Asset, AssetStatus, AssetType
from app.models.geography import AssetGeoTag
from app.models.user import User
from app.schemas.asset import GeoEntitySummary
from app.schemas.newspaper import NewspaperClippingItem, NewspaperListResponse
from app.services.geography import GeographyService

router = APIRouter(prefix="/newspapers", tags=["Newspaper Archive"])


@router.get("", response_model=NewspaperListResponse)
async def list_newspaper_clippings(
    newspaper_name: str | None = Query(None, description="Filter by publication name (e.g. Eenadu)"),
    edition: str | None = Query(None, description="Filter by edition (e.g. Amaravati)"),
    date_from: str | None = Query(None, description="Filter publication date from (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="Filter publication date to (YYYY-MM-DD)"),
    geo_id: uuid.UUID | None = Query(None, description="Filter by geographic entity with alias expansion"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> NewspaperListResponse:
    """List and filter published newspaper clippings with presigned preview URLs and geo tags."""
    where_clauses = [
        Asset.asset_type == AssetType.NEWSPAPER_CLIPPING,
        Asset.status == AssetStatus.PUBLISHED,
    ]

    if newspaper_name:
        where_clauses.append(
            Asset.dynamic_metadata["newspaper_name"].as_string().ilike(f"%{newspaper_name}%")
        )

    if edition:
        where_clauses.append(
            Asset.dynamic_metadata["edition"].as_string().ilike(f"%{edition}%")
        )

    if date_from:
        where_clauses.append(
            Asset.dynamic_metadata["publication_date"].as_string() >= date_from
        )

    if date_to:
        where_clauses.append(
            Asset.dynamic_metadata["publication_date"].as_string() <= date_to
        )

    if geo_id:
        expanded_ids = await GeographyService.resolve_geo_filter_ids(db, [geo_id])
        if not expanded_ids:
            return NewspaperListResponse(
                items=[],
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0,
            )
        where_clauses.append(
            Asset.id.in_(
                select(AssetGeoTag.asset_id).where(AssetGeoTag.geo_entity_id.in_(expanded_ids))
            )
        )

    # Count total matching clippings
    count_stmt = select(func.count(Asset.id)).where(*where_clauses)
    total = (await db.scalar(count_stmt)) or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    # Fetch paginated clippings with geo entities
    data_stmt = (
        select(Asset)
        .where(*where_clauses)
        .options(selectinload(Asset.geo_entities))
        .order_by(
            Asset.dynamic_metadata["publication_date"].as_string().desc(),
            Asset.created_at.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    assets = (await db.execute(data_stmt)).scalars().all()

    storage = get_storage_provider()
    items: list[NewspaperClippingItem] = []

    for a in assets:
        meta = a.dynamic_metadata or {}
        preview_url = storage.generate_download_url(a.r2_object_key, expires_sec=300)
        headline = str(meta.get("headline") or a.title)
        pub_name = str(meta.get("newspaper_name") or a.source_name or "Unknown")
        edition_val = meta.get("edition")
        pub_date = str(meta.get("publication_date") or "")
        page_num = meta.get("page_number")

        geo_summaries = [
            GeoEntitySummary(
                id=g.id,
                name=g.name,
                telugu_name=g.telugu_name,
                tier=g.tier,
                code=g.code,
            )
            for g in (a.geo_entities or [])
        ]

        items.append(
            NewspaperClippingItem(
                id=a.id,
                headline=headline,
                newspaper_name=pub_name,
                edition=str(edition_val) if edition_val is not None else None,
                publication_date=pub_date,
                page_number=page_num,
                extracted_text=a.extracted_text,
                geo_tags=geo_summaries,
                preview_url=preview_url,
                created_at=a.created_at,
            )
        )

    return NewspaperListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
