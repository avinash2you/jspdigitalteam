import pytest
from pydantic import ValidationError

from app.models.asset import AssetType
from app.schemas.asset_metadata import (
    GovernmentDocumentMetadata,
    ImageInfographicMetadata,
    NewspaperClippingMetadata,
    OnlineNewsSocialMetadata,
    ResearchMaterialMetadata,
    VideoAudioMetadata,
    validate_dynamic_metadata,
)


def test_government_document_metadata_valid():
    data = {
        "go_number": "GO-MS-104",
        "issuing_department": "Revenue Department",
        "date_of_issue": "2024-03-01",
        "subject": "Land Regularization in Urban Areas",
        "state": "Andhra Pradesh",
    }
    obj = GovernmentDocumentMetadata.model_validate(data)
    assert obj.go_number == "GO-MS-104"
    assert obj.issuing_department == "Revenue Department"
    assert obj.district_local_body is None

    # With optional fields
    data_opt = {
        **data,
        "district_local_body": "Visakhapatnam",
        "related_scheme": "Housing Scheme",
        "effective_date": "2024-04-01",
        "supersedes_go_number": "GO-MS-50",
    }
    obj_opt = GovernmentDocumentMetadata.model_validate(data_opt)
    assert obj_opt.district_local_body == "Visakhapatnam"
    assert obj_opt.supersedes_go_number == "GO-MS-50"


def test_government_document_metadata_invalid_missing_required():
    with pytest.raises(ValidationError) as exc_info:
        GovernmentDocumentMetadata.model_validate({"go_number": "GO-1"})
    errors = {e["loc"][0] for e in exc_info.value.errors()}
    assert "issuing_department" in errors
    assert "date_of_issue" in errors
    assert "subject" in errors
    assert "state" in errors


def test_newspaper_clipping_metadata_valid():
    data = {
        "newspaper_name": "Eenadu",
        "publication_date": "2024-02-15",
        "headline": "Major Policy Announcement",
    }
    obj = NewspaperClippingMetadata.model_validate(data)
    assert obj.newspaper_name == "Eenadu"
    assert obj.page_number is None

    # With optional fields
    data_opt = {
        **data,
        "edition": "Amaravati",
        "page_number": 3,
        "column_byline": "Special Correspondent",
    }
    obj_opt = NewspaperClippingMetadata.model_validate(data_opt)
    assert obj_opt.edition == "Amaravati"
    assert obj_opt.page_number == 3


def test_newspaper_clipping_metadata_invalid():
    with pytest.raises(ValidationError) as exc_info:
        NewspaperClippingMetadata.model_validate({"headline": "Title Only"})
    errors = {e["loc"][0] for e in exc_info.value.errors()}
    assert "newspaper_name" in errors
    assert "publication_date" in errors


def test_online_news_social_metadata_valid():
    data = {
        "platform_publisher": "X (Twitter)",
        "source_url": "https://x.com/janasenaparty/status/123456789",
        "published_date": "2024-03-10",
        "author_handle": "@PawanKalyan",
    }
    obj = OnlineNewsSocialMetadata.model_validate(data)
    assert obj.platform_publisher == "X (Twitter)"
    assert obj.author_handle == "@PawanKalyan"

    # With optional
    data_opt = {**data, "key_quote": "Stand with people."}
    obj_opt = OnlineNewsSocialMetadata.model_validate(data_opt)
    assert obj_opt.key_quote == "Stand with people."


def test_online_news_social_metadata_invalid():
    with pytest.raises(ValidationError):
        OnlineNewsSocialMetadata.model_validate({})


def test_video_audio_metadata_valid():
    data = {
        "source_channel_event": "JanaSena Official YouTube",
        "recording_date": "2024-03-12",
        "speakers": ["Pawan Kalyan", "Nadendla Manohar"],
    }
    obj = VideoAudioMetadata.model_validate(data)
    assert len(obj.speakers) == 2
    assert obj.duration_sec is None

    # With optional
    data_opt = {
        **data,
        "duration_sec": 3600.5,
        "venue": "Mangalagiri Party HQ",
        "key_timestamps": {"00:15:30": "Discussion on youth employment"},
    }
    obj_opt = VideoAudioMetadata.model_validate(data_opt)
    assert obj_opt.duration_sec == 3600.5
    assert obj_opt.venue == "Mangalagiri Party HQ"
    assert "00:15:30" in obj_opt.key_timestamps


def test_video_audio_metadata_empty_speakers_invalid():
    with pytest.raises(ValidationError):
        VideoAudioMetadata.model_validate(
            {
                "source_channel_event": "Speech",
                "recording_date": "2024-03-12",
                "speakers": [],
            }
        )


def test_image_infographic_metadata_valid():
    data = {
        "event_subject": "Varahi Vijaya Yatra Rally",
        "capture_date": "2024-02-20",
        "credit_source": "JSP Digital Team Media Wing",
    }
    obj = ImageInfographicMetadata.model_validate(data)
    assert obj.event_subject == "Varahi Vijaya Yatra Rally"

    # With optional
    data_opt = {
        **data,
        "people_depicted": ["Pawan Kalyan", "Supporters"],
        "caption": "Public gathering at Kakinada",
        "usage_rights": "Editorial only",
    }
    obj_opt = ImageInfographicMetadata.model_validate(data_opt)
    assert len(obj_opt.people_depicted) == 2
    assert obj_opt.caption == "Public gathering at Kakinada"


def test_image_infographic_metadata_invalid():
    with pytest.raises(ValidationError):
        ImageInfographicMetadata.model_validate({"credit_source": "Media"})


def test_research_material_metadata_valid():
    data = {
        "document_title": "Andhra Pradesh Agricultural Debt Analysis 2019-2024",
        "authoring_body": "JSP Policy & Research Cell",
        "publication_date": "2024-01-10",
    }
    obj = ResearchMaterialMetadata.model_validate(data)
    assert obj.document_title.startswith("Andhra Pradesh")

    # With optional
    data_opt = {
        **data,
        "sample_size_methodology": "Field surveys of 1,200 smallholder farmers in 10 districts",
        "executive_summary": "High reliance on non-institutional credit.",
        "key_metrics": {"indebtedness_rate": "82%", "avg_debt_inr": 245000},
    }
    obj_opt = ResearchMaterialMetadata.model_validate(data_opt)
    assert obj_opt.key_metrics["indebtedness_rate"] == "82%"


def test_research_material_metadata_invalid():
    with pytest.raises(ValidationError):
        ResearchMaterialMetadata.model_validate({})


def test_validate_dynamic_metadata_dispatcher():
    # Valid dispatch
    validated = validate_dynamic_metadata(
        AssetType.GOVERNMENT_DOCUMENT.value,
        {
            "go_number": "GO-101",
            "issuing_department": "Finance",
            "date_of_issue": "2024-01-01",
            "subject": "Budget Allocation",
            "state": "AP",
        },
    )
    assert isinstance(validated, GovernmentDocumentMetadata)
    assert validated.go_number == "GO-101"

    # Invalid asset type raises ValueError
    with pytest.raises(ValueError, match="Unsupported asset_type: 'unknown_type'"):
        validate_dynamic_metadata("unknown_type", {})
