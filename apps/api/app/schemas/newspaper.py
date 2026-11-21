import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.asset import GeoEntitySummary


class NewspaperClippingItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    headline: str
    newspaper_name: str
    edition: str | None = None
    publication_date: str
    page_number: int | str | None = None
    extracted_text: str | None = None
    geo_tags: list[GeoEntitySummary] = Field(default_factory=list)
    preview_url: str
    created_at: datetime


class NewspaperListResponse(BaseModel):
    items: list[NewspaperClippingItem] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    total_pages: int
