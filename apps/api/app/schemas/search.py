from pydantic import BaseModel, Field

from app.adapters.base import SearchResultItem


class SearchPaginationResponse(BaseModel):
    items: list[SearchResultItem] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    total_pages: int
