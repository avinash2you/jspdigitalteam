from app.adapters.base import (
    AIExtractionResult,
    AIProvider,
    AssetSearchDocument,
    ObjectMetadata,
    OCRPage,
    OCRProvider,
    OCRResult,
    SearchFilters,
    SearchProvider,
    SearchResponse,
    SearchResultItem,
    StorageProvider,
)
from app.adapters.storage_r2 import R2StorageProvider
from app.core.config import settings

# ============================================================================
# In-Memory Mock Implementations
# ============================================================================


class MockStorageProvider:
    """In-memory mock storage provider for unit testing."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, ObjectMetadata]] = {}

    def generate_upload_url(self, key: str, content_type: str, expires_sec: int = 900) -> str:
        return f"https://mock-storage.local/upload/{key}?expires={expires_sec}&type={content_type}"

    def generate_download_url(self, key: str, expires_sec: int = 900) -> str:
        return f"https://mock-storage.local/download/{key}?expires={expires_sec}"

    def head_object(self, key: str) -> ObjectMetadata:
        if key not in self.objects:
            return ObjectMetadata(
                key=key,
                size=1024,
                content_type="application/octet-stream",
                etag="mock-etag-123",
                last_modified="2026-11-21T00:00:00Z",
            )
        _, meta = self.objects[key]
        return meta

    def delete_object(self, key: str) -> None:
        self.objects.pop(key, None)


class MockOCRProvider:
    """Deterministic mock OCR provider for unit testing."""

    def extract_text(self, file_bytes: bytes, mime_type: str, languages: list[str]) -> OCRResult:
        full_text = f"Mock OCR Extracted Text for {len(file_bytes)} bytes ({mime_type})"
        page = OCRPage(page_number=1, text=full_text, confidence=0.98)
        return OCRResult(
            full_text=full_text,
            pages=[page],
            boxes_json={"blocks": [{"text": full_text, "bbox": [0, 0, 100, 100]}]},
        )


class MockSearchProvider:
    """In-memory mock search index for unit testing."""

    def __init__(self) -> None:
        self.documents: dict[str, AssetSearchDocument] = {}

    def index_asset(self, asset_doc: AssetSearchDocument) -> None:
        self.documents[asset_doc.id] = asset_doc

    def delete_asset(self, asset_id: str) -> None:
        self.documents.pop(asset_id, None)

    def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> SearchResponse:
        results: list[SearchResultItem] = []
        q = query.lower()
        for doc in self.documents.values():
            if filters and filters.asset_type and doc.asset_type != filters.asset_type:
                continue
            text = (doc.title + " " + (doc.content_text or "")).lower()
            if q in text or not q:
                results.append(
                    SearchResultItem(
                        id=doc.id,
                        title=doc.title,
                        snippet=doc.description or doc.title,
                        score=1.0,
                        asset_type=doc.asset_type,
                    )
                )
        paginated = results[offset : offset + limit]
        return SearchResponse(
            total=len(results),
            items=paginated,
            limit=limit,
            offset=offset,
        )


class MockAIProvider:
    """Mock AI extraction provider with privacy guardrails."""

    def extract_metadata_and_summary(
        self, text_or_bytes: str | bytes, asset_type: str, is_public: bool
    ) -> AIExtractionResult:
        # AGENTS.md rule: confidential documents cannot use free-tier extraction
        if not is_public and getattr(settings, "AI_BACKEND", "mock") == "gemini_free":
            raise PermissionError(
                "Confidential documents cannot be processed by free-tier AI keys."
            )
        text_str = (
            text_or_bytes
            if isinstance(text_or_bytes, str)
            else text_or_bytes.decode(errors="ignore")
        )
        summary = f"Mock summary for {asset_type} ({len(text_str)} chars)"
        return AIExtractionResult(
            title=f"Extracted {asset_type}",
            summary=summary,
            tags=["mock", asset_type],
            entities=["AP", "JSP"],
            confidence=0.95,
            raw_output={"mock": True},
        )


# ============================================================================
# Adapter Dependency Getters & Registry
# ============================================================================

_storage_instances: dict[str, StorageProvider] = {"mock": MockStorageProvider()}
_ocr_instances: dict[str, OCRProvider] = {"mock": MockOCRProvider()}
_search_instances: dict[str, SearchProvider] = {"mock": MockSearchProvider()}
_ai_instances: dict[str, AIProvider] = {"mock": MockAIProvider()}


def get_storage_provider(backend: str | None = None) -> StorageProvider:
    selected = (backend or settings.STORAGE_BACKEND).lower()
    if selected in ("mock", "memory"):
        return _storage_instances["mock"]
    elif selected in ("r2", "cloudflare_r2"):
        if "r2" not in _storage_instances:
            _storage_instances["r2"] = R2StorageProvider()
        return _storage_instances["r2"]
    elif selected in ("minio", "s3"):
        raise NotImplementedError(
            f"Storage backend '{selected}' will be implemented in subsequent task."
        )
    raise ValueError(f"Unsupported storage backend: '{selected}'")


def get_ocr_provider(backend: str | None = None) -> OCRProvider:
    selected = (backend or settings.OCR_BACKEND).lower()
    if selected in ("mock", "memory"):
        return _ocr_instances["mock"]
    elif selected in ("tesseract", "pytesseract"):
        if "tesseract" not in _ocr_instances:
            from app.adapters.ocr_tesseract import TesseractOCRProvider

            _ocr_instances["tesseract"] = TesseractOCRProvider()
        return _ocr_instances["tesseract"]
    elif selected in ("document_ai", "cloud_document_ai"):
        # Concrete implementation in Milestone 2
        raise NotImplementedError(
            f"OCR backend '{selected}' will be implemented in subsequent task."
        )
    raise ValueError(f"Unsupported OCR backend: '{selected}'")


def get_search_provider(backend: str | None = None) -> SearchProvider:
    selected = (backend or settings.SEARCH_BACKEND).lower()
    if selected in ("mock", "memory"):
        return _search_instances["mock"]
    elif selected in ("postgres_hybrid", "postgres", "meilisearch"):
        # Concrete implementation wired in T10
        raise NotImplementedError(
            f"Search backend '{selected}' will be implemented in subsequent task."
        )
    raise ValueError(f"Unsupported search backend: '{selected}'")


def get_ai_provider(backend: str | None = None) -> AIProvider:
    selected = (backend or settings.AI_BACKEND).lower()
    if selected in ("mock", "memory"):
        return _ai_instances["mock"]
    elif selected in ("gemini_free", "gemini_paid", "gemini"):
        # Concrete implementation wired in T20
        raise NotImplementedError(
            f"AI backend '{selected}' will be implemented in subsequent task."
        )
    raise ValueError(f"Unsupported AI backend: '{selected}'")
