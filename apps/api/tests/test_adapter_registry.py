import pytest

from app.adapters.base import (
    AIExtractionResult,
    AIProvider,
    AssetSearchDocument,
    ObjectMetadata,
    OCRProvider,
    OCRResult,
    SearchFilters,
    SearchProvider,
    SearchResponse,
    StorageProvider,
)
from app.adapters.registry import (
    MockAIProvider,
    MockOCRProvider,
    MockSearchProvider,
    MockStorageProvider,
    get_ai_provider,
    get_ocr_provider,
    get_search_provider,
    get_storage_provider,
)


def test_storage_provider_protocol_and_mock() -> None:
    provider = get_storage_provider("mock")
    assert isinstance(provider, StorageProvider)
    assert isinstance(provider, MockStorageProvider)

    # Test upload URL generation
    upload_url = provider.generate_upload_url("assets/test.pdf", "application/pdf", expires_sec=600)
    assert "mock-storage.local" in upload_url
    assert "assets/test.pdf" in upload_url
    assert "expires=600" in upload_url

    # Test download URL generation
    download_url = provider.generate_download_url("assets/test.pdf", expires_sec=300)
    assert "mock-storage.local" in download_url
    assert "assets/test.pdf" in download_url
    assert "expires=300" in download_url

    # Test head object
    meta = provider.head_object("assets/test.pdf")
    assert isinstance(meta, ObjectMetadata)
    assert meta.key == "assets/test.pdf"

    # Test delete
    provider.delete_object("assets/test.pdf")


def test_ocr_provider_protocol_and_mock() -> None:
    provider = get_ocr_provider("mock")
    assert isinstance(provider, OCRProvider)
    assert isinstance(provider, MockOCRProvider)

    result = provider.extract_text(b"sample bytes", "application/pdf", ["tel", "eng"])
    assert isinstance(result, OCRResult)
    assert len(result.pages) == 1
    assert result.pages[0].confidence == 0.98
    assert "Mock OCR" in result.full_text
    assert "blocks" in result.boxes_json


def test_search_provider_protocol_and_mock() -> None:
    provider = get_search_provider("mock")
    assert isinstance(provider, SearchProvider)
    assert isinstance(provider, MockSearchProvider)

    doc = AssetSearchDocument(
        id="asset-1",
        title="JSP Manifesto 2024",
        description="Official political manifesto",
        content_text="Detailed policy document on welfare and development in Andhra Pradesh",
        asset_type="document",
        tags=["manifesto", "welfare"],
    )
    provider.index_asset(doc)

    # Substring search
    resp = provider.search("manifesto")
    assert isinstance(resp, SearchResponse)
    assert resp.total >= 1
    assert resp.items[0].id == "asset-1"

    # Filtered search
    filter_resp = provider.search("manifesto", filters=SearchFilters(asset_type="image"))
    assert filter_resp.total == 0

    # Delete
    provider.delete_asset("asset-1")
    after_del = provider.search("manifesto")
    assert after_del.total == 0


def test_ai_provider_protocol_and_mock() -> None:
    provider = get_ai_provider("mock")
    assert isinstance(provider, AIProvider)
    assert isinstance(provider, MockAIProvider)

    result = provider.extract_metadata_and_summary(
        "Press release regarding youth welfare schemes",
        asset_type="press_clipping",
        is_public=True,
    )
    assert isinstance(result, AIExtractionResult)
    assert "press_clipping" in result.summary
    assert "AP" in result.entities
    assert result.confidence == 0.95


def test_registry_raises_on_unknown_backend() -> None:
    with pytest.raises(ValueError, match="Unsupported storage backend"):
        get_storage_provider("unsupported_backend")

    with pytest.raises(ValueError, match="Unsupported OCR backend"):
        get_ocr_provider("unsupported_backend")

    with pytest.raises(ValueError, match="Unsupported search backend"):
        get_search_provider("unsupported_backend")

    with pytest.raises(ValueError, match="Unsupported AI backend"):
        get_ai_provider("unsupported_backend")


def test_registry_raises_not_implemented_on_unwired_concrete_backends() -> None:
    with pytest.raises(NotImplementedError, match="Storage backend 'r2'"):
        get_storage_provider("r2")

    with pytest.raises(NotImplementedError, match="OCR backend 'tesseract'"):
        get_ocr_provider("tesseract")

    with pytest.raises(NotImplementedError, match="Search backend 'postgres_hybrid'"):
        get_search_provider("postgres_hybrid")

    with pytest.raises(NotImplementedError, match="AI backend 'gemini_free'"):
        get_ai_provider("gemini_free")
