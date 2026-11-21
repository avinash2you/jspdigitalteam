import json
from unittest.mock import MagicMock, patch

import pytest

from app.adapters.ai_gemini import (
    ConfidentialDataBlockedError,
    GeminiAIProvider,
    GeminiExtractionOutput,
)
from app.adapters.base import AIExtractionResult, AIProvider
from app.adapters.registry import get_ai_provider


def test_gemini_provider_conforms_to_protocol() -> None:
    provider = GeminiAIProvider(api_key="test-key", tier="free")
    assert isinstance(provider, AIProvider)


def test_registry_selects_gemini_provider() -> None:
    provider_free = get_ai_provider("gemini_free")
    assert isinstance(provider_free, GeminiAIProvider)
    assert provider_free.tier == "free"

    provider_paid = get_ai_provider("gemini_paid")
    assert isinstance(provider_paid, GeminiAIProvider)
    assert provider_paid.tier == "paid"


def test_confidential_data_hard_blocked_on_free_tier() -> None:
    provider = GeminiAIProvider(api_key="test-key", tier="free")

    with patch.object(provider, "_get_client") as mock_get_client:
        with pytest.raises(ConfidentialDataBlockedError) as exc_info:
            provider.extract_metadata_and_summary(
                text_or_bytes="Confidential internal party strategy note.",
                asset_type="research_material",
                is_public=False,
            )

        assert "Confidential documents cannot be processed by free-tier AI keys" in str(
            exc_info.value
        )
        # Verify the client is NEVER accessed or called
        mock_get_client.assert_not_called()


def test_confidential_data_allowed_on_paid_tier() -> None:
    provider = GeminiAIProvider(api_key="test-key", tier="paid")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(
        {
            "suggested_metadata": {"document_title": "Internal Strategy"},
            "english_summary": "Summary of internal strategy.",
            "tenglish_keywords": ["vyuharachana"],
            "suggested_geo_names": ["Vijayawada"],
        }
    )
    mock_client.models.generate_content.return_value = mock_response

    with patch.object(provider, "_get_client", return_value=mock_client):
        result = provider.extract_metadata_and_summary(
            text_or_bytes="Internal party note.",
            asset_type="research_material",
            is_public=False,
        )

        assert mock_client.models.generate_content.called
        assert isinstance(result, AIExtractionResult)
        assert result.title == "Internal Strategy"
        assert result.summary == "Summary of internal strategy."


def test_public_data_allowed_on_free_tier() -> None:
    provider = GeminiAIProvider(api_key="test-key", tier="free")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(
        {
            "suggested_metadata": {
                "go_number": "GO-MS-104",
                "issuing_department": "Revenue",
                "subject": "Land allotment",
                "state": "Andhra Pradesh",
            },
            "english_summary": "Order regarding land allotment in Vizag.",
            "tenglish_keywords": ["bhoomi", "allotment", "vizag"],
            "suggested_geo_names": ["Visakhapatnam", "Andhra Pradesh"],
        }
    )
    mock_client.models.generate_content.return_value = mock_response

    with patch.object(provider, "_get_client", return_value=mock_client):
        result = provider.extract_metadata_and_summary(
            text_or_bytes="Government Order 104 Revenue Department...",
            asset_type="government_document",
            is_public=True,
        )

        assert mock_client.models.generate_content.called
        assert isinstance(result, AIExtractionResult)
        assert result.title == "Land allotment"
        assert result.summary == "Order regarding land allotment in Vizag."
        assert "bhoomi" in result.tags
        assert "Visakhapatnam" in result.entities
        assert result.raw_output["suggested_metadata"]["go_number"] == "GO-MS-104"


def test_mocked_gemini_response_parsing_all_fields() -> None:
    provider = GeminiAIProvider(api_key="test-key", tier="free")

    mock_client = MagicMock()
    mock_response = MagicMock()
    expected_data = {
        "suggested_metadata": {
            "newspaper_name": "Eenadu",
            "publication_date": "2024-03-15",
            "headline": "Varahi Yatra in Godavari",
            "edition": "Rajahmundry",
        },
        "english_summary": "Pawan Kalyan addressed large crowds in Rajahmundry on farmer issues.",
        "tenglish_keywords": ["varahi", "yatra", "rythu", "godavari", "sabha"],
        "suggested_geo_names": ["Rajahmundry", "East Godavari"],
    }
    mock_response.text = json.dumps(expected_data)
    mock_client.models.generate_content.return_value = mock_response

    with patch.object(provider, "_get_client", return_value=mock_client):
        output = provider.extract_document_intelligence(
            text_or_bytes="Eenadu article text on Varahi yatra...",
            asset_type="newspaper_clipping",
            is_public=True,
        )

        assert isinstance(output, GeminiExtractionOutput)
        assert output.suggested_metadata["newspaper_name"] == "Eenadu"
        assert output.suggested_metadata["headline"] == "Varahi Yatra in Godavari"
        assert "Pawan Kalyan" in output.english_summary
        assert output.tenglish_keywords == ["varahi", "yatra", "rythu", "godavari", "sabha"]
        assert output.suggested_geo_names == ["Rajahmundry", "East Godavari"]


def test_empty_text_returns_empty_without_api_call() -> None:
    provider = GeminiAIProvider(api_key="test-key", tier="free")
    with patch.object(provider, "_get_client") as mock_get_client:
        result = provider.extract_metadata_and_summary(
            text_or_bytes="   ",
            asset_type="newspaper_clipping",
            is_public=True,
        )
        mock_get_client.assert_not_called()
        assert result.summary == ""
        assert result.tags == []
        assert result.entities == []


def test_rate_limit_error_degrades_gracefully() -> None:
    provider = GeminiAIProvider(api_key="test-key", tier="free")

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError(
        "429 ResourceExhausted: Quota exceeded for quota metric 'GenerateContent'"
    )

    with patch.object(provider, "_get_client", return_value=mock_client):
        result = provider.extract_metadata_and_summary(
            text_or_bytes="Some public document text",
            asset_type="government_document",
            is_public=True,
        )

        assert isinstance(result, AIExtractionResult)
        assert "temporarily unavailable due to rate limits" in result.summary
        assert result.confidence == 0.0
