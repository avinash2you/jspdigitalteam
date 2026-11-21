import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.geography import (
    GeographyService,
    GeoSearchResultItem,
    GeoTreeResponse,
)

router = APIRouter(prefix="/geography", tags=["Geography & Administration"])


class ResolveGeoFiltersRequest(BaseModel):
    geo_ids: list[uuid.UUID]


class ResolveGeoFiltersResponse(BaseModel):
    resolved_ids: list[uuid.UUID]


@router.get("/search", response_model=list[GeoSearchResultItem])
async def search_geography(
    q: str | None = Query(default=None, description="Search query by name, Telugu name, or alias"),
    tier: str | None = Query(default=None, description="Optional administrative tier filter"),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[GeoSearchResultItem]:
    """Search geographic entities and historical pre-2022 aliases."""
    return await GeographyService.search_geography(db, q=q, tier=tier, limit=limit)


@router.get("/{entity_id}/tree", response_model=GeoTreeResponse)
async def get_geography_tree(
    entity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> GeoTreeResponse:
    """Retrieve full ancestor lineage and immediate child entities for a geographic entity."""
    tree = await GeographyService.get_geo_tree(db, entity_id)
    if tree is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Geographic entity not found",
        )
    return tree


@router.post("/resolve-filters", response_model=ResolveGeoFiltersResponse)
async def resolve_geography_filters(
    payload: ResolveGeoFiltersRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> ResolveGeoFiltersResponse:
    """Resolve given geographic IDs to include their full hierarchical descendant tree and pre-2022 aliases."""
    resolved = await GeographyService.resolve_geo_filter_ids(db, payload.geo_ids)
    return ResolveGeoFiltersResponse(resolved_ids=list(resolved))
