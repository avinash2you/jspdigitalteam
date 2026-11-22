import math
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.base import SearchFilters
from app.adapters.registry import get_search_provider
from app.adapters.search_postgres import PostgresHybridSearchProvider
from app.core.permissions import Permission, require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.search import SearchPaginationResponse

router = APIRouter(prefix="/search", tags=["Advanced Search"])
require_search_permission = require_permission(Permission.SEARCH_USE)


@router.get("", response_model=SearchPaginationResponse)
async def search_assets(
    q: str | None = Query(None, description="Search query across English, Telugu, and Tenglish"),
    geo_ids: list[uuid.UUID] = Query(default_factory=list, description="Filter by geographic entities with alias expansion"),
    asset_types: list[str] = Query(default_factory=list, description="Filter by asset types"),
    date_from: str | None = Query(None, description="Filter publication date from (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="Filter publication date to (YYYY-MM-DD)"),
    department: str | None = Query(None, description="Filter by issuing department"),
    verification_status: str | None = Query(None, description="Filter by verification status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_search_permission),
) -> SearchPaginationResponse:
    """Execute multilingual hybrid search combining FTS, trigram, exact GO match, and geo expansion."""
    filters = SearchFilters(
        asset_types=asset_types,
        date_from=date_from,
        date_to=date_to,
        geo_ids=geo_ids,
        department=department,
        verification_status=verification_status,
    )

    offset = (page - 1) * page_size
    provider = get_search_provider()

    if isinstance(provider, PostgresHybridSearchProvider):
        search_res = await provider.asearch(
            query=q or "",
            filters=filters,
            limit=page_size,
            offset=offset,
            session=db,
        )
    else:
        search_res = provider.search(
            query=q or "",
            filters=filters,
            limit=page_size,
            offset=offset,
        )

    total_pages = math.ceil(search_res.total / page_size) if search_res.total > 0 else 0

    return SearchPaginationResponse(
        items=search_res.items,
        total=search_res.total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
