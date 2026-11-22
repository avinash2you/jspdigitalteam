import uuid
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

# ============================================================================
# Storage DTOs & Protocol
# ============================================================================


class ObjectMetadata(BaseModel):
    key: str
    size: int
    content_type: str
    etag: str | None = None
    last_modified: str | None = None


@runtime_checkable
class StorageProvider(Protocol):
    def generate_upload_url(self, key: str, content_type: str, expires_sec: int = 900) -> str:
        """Generate a short-lived presigned URL for private direct upload."""
        ...

    def generate_download_url(self, key: str, expires_sec: int = 900) -> str:
        """Generate a short-lived presigned URL for private read access."""
        ...

    def head_object(self, key: str) -> ObjectMetadata:
        """Retrieve metadata for an existing object."""
        ...

    def delete_object(self, key: str) -> None:
        """Permanently delete an object by key."""
        ...

    def get_object(self, key: str) -> bytes:
        """Download and return raw object bytes."""
        ...


# ============================================================================
# OCR DTOs & Protocol
# ============================================================================


class OCRPage(BaseModel):
    page_number: int
    text: str
    confidence: float | None = None


class OCRResult(BaseModel):
    full_text: str
    pages: list[OCRPage] = Field(default_factory=list)
    boxes_json: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class OCRProvider(Protocol):
    def extract_text(self, file_bytes: bytes, mime_type: str, languages: list[str]) -> OCRResult:
        """Extract multi-lingual text and layout bounding boxes from document or image."""
        ...


# ============================================================================
# Search DTOs & Protocol
# ============================================================================


class AssetSearchDocument(BaseModel):
    id: str
    title: str
    description: str | None = None
    content_text: str | None = None
    asset_type: str = "document"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchFilters(BaseModel):
    asset_type: str | None = None
    asset_types: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    geo_ids: list[uuid.UUID] = Field(default_factory=list)
    department: str | None = None
    verification_status: str | None = None


class SearchResultItem(BaseModel):
    id: str
    title: str
    snippet: str
    score: float
    asset_type: str
    headline: str | None = None
    highlighted_snippet: str | None = None
    go_number: str | None = None
    publication_date: str | None = None
    source_name: str | None = None
    preview_url: str | None = None
    geo_tags: list[dict[str, Any]] = Field(default_factory=list)


class SearchResponse(BaseModel):
    total: int
    items: list[SearchResultItem] = Field(default_factory=list)
    limit: int = 20
    offset: int = 0


@runtime_checkable
class SearchProvider(Protocol):
    def index_asset(self, asset_doc: AssetSearchDocument) -> None:
        """Index or update an asset document into the search backend."""
        ...

    def delete_asset(self, asset_id: str) -> None:
        """Remove an asset document from the search index."""
        ...

    def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> SearchResponse:
        """Execute text or hybrid search across indexed assets."""
        ...


# ============================================================================
# AI Extraction DTOs & Protocol
# ============================================================================


class AIExtractionResult(BaseModel):
    title: str | None = None
    summary: str = ""
    tags: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    raw_output: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class AIProvider(Protocol):
    def extract_metadata_and_summary(
        self, text_or_bytes: str | bytes, asset_type: str, is_public: bool
    ) -> AIExtractionResult:
        """Extract metadata, entity tags, and summary. Enforces privacy guardrails."""
        ...
