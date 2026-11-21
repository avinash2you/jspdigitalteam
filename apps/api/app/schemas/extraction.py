import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.models.asset import AssetStatus


class ExtractionResponse(BaseModel):
    asset_id: uuid.UUID
    extracted_text: str
    english_summary: str | None = None
    tenglish_keywords: list[str] = Field(default_factory=list)
    suggested_metadata: dict[str, Any] = Field(default_factory=dict)
    suggested_geo_names: list[str] = Field(default_factory=list)
    ai_skipped: bool
    ai_notice: str | None = None
    status: AssetStatus


class PublishRequest(BaseModel):
    extracted_text: str = Field(min_length=1)
    english_summary: str | None = None
    tenglish_keywords: list[str] = Field(default_factory=list)
    dynamic_metadata: dict[str, Any] = Field(default_factory=dict)
    geo_entity_ids: list[uuid.UUID] | None = None
