from typing import Annotated, Any

from pydantic import BaseModel, Field

from app.models.asset import AssetType


class GovernmentDocumentMetadata(BaseModel):
    go_number: Annotated[str, Field(min_length=1, description="Government Order Number")]
    issuing_department: Annotated[
        str, Field(min_length=1, description="Issuing Department or Ministry")
    ]
    date_of_issue: Annotated[str, Field(min_length=1, description="Issue date (YYYY-MM-DD)")]
    subject: Annotated[str, Field(min_length=1, description="Official subject line")]
    state: Annotated[str, Field(min_length=1, description="State or Union Territory")]
    district_local_body: str | None = None
    related_scheme: str | None = None
    effective_date: str | None = None
    supersedes_go_number: str | None = None


class NewspaperClippingMetadata(BaseModel):
    newspaper_name: Annotated[str, Field(min_length=1, description="Publication name")]
    publication_date: Annotated[
        str, Field(min_length=1, description="Publication date (YYYY-MM-DD)")
    ]
    headline: Annotated[str, Field(min_length=1, description="Article headline")]
    edition: str | None = None
    page_number: int | str | None = None
    column_byline: str | None = None


class OnlineNewsSocialMetadata(BaseModel):
    platform_publisher: Annotated[str, Field(min_length=1, description="Platform or Website name")]
    source_url: Annotated[str, Field(min_length=1, description="Source URL")]
    published_date: Annotated[
        str, Field(min_length=1, description="Published date (YYYY-MM-DD)")
    ]
    author_handle: Annotated[
        str, Field(min_length=1, description="Author name or social handle")
    ]
    key_quote: str | None = None


class VideoAudioMetadata(BaseModel):
    source_channel_event: Annotated[
        str, Field(min_length=1, description="Source channel, broadcaster, or event name")
    ]
    recording_date: Annotated[
        str, Field(min_length=1, description="Recording date (YYYY-MM-DD)")
    ]
    speakers: Annotated[list[str], Field(min_length=1, description="List of recognized speakers")]
    duration_sec: float | int | None = None
    venue: str | None = None
    key_timestamps: dict[str, Any] | None = None


class ImageInfographicMetadata(BaseModel):
    event_subject: Annotated[str, Field(min_length=1, description="Event or subject depicted")]
    capture_date: Annotated[str, Field(min_length=1, description="Capture date (YYYY-MM-DD)")]
    credit_source: Annotated[str, Field(min_length=1, description="Photographer or credit source")]
    people_depicted: list[str] | None = None
    caption: str | None = None
    usage_rights: str | None = None


class ResearchMaterialMetadata(BaseModel):
    document_title: Annotated[str, Field(min_length=1, description="Research or report title")]
    authoring_body: Annotated[
        str, Field(min_length=1, description="Authoring institute or analyst")
    ]
    publication_date: Annotated[
        str, Field(min_length=1, description="Publication date (YYYY-MM-DD)")
    ]
    sample_size_methodology: str | None = None
    executive_summary: str | None = None
    key_metrics: dict[str, Any] | None = None


DynamicMetadataType = (
    GovernmentDocumentMetadata
    | NewspaperClippingMetadata
    | OnlineNewsSocialMetadata
    | VideoAudioMetadata
    | ImageInfographicMetadata
    | ResearchMaterialMetadata
)

ASSET_TYPE_SCHEMA_MAP: dict[str, type[BaseModel]] = {
    AssetType.GOVERNMENT_DOCUMENT.value: GovernmentDocumentMetadata,
    AssetType.NEWSPAPER_CLIPPING.value: NewspaperClippingMetadata,
    AssetType.ONLINE_NEWS_SOCIAL.value: OnlineNewsSocialMetadata,
    AssetType.VIDEO_AUDIO.value: VideoAudioMetadata,
    AssetType.IMAGE_INFOGRAPHIC.value: ImageInfographicMetadata,
    AssetType.RESEARCH_MATERIAL.value: ResearchMaterialMetadata,
}


def validate_dynamic_metadata(asset_type: str, data: dict[str, Any]) -> BaseModel:
    """Validate dynamic metadata payload strictly against the type-specific Pydantic schema."""
    schema_cls = ASSET_TYPE_SCHEMA_MAP.get(asset_type)
    if schema_cls is None:
        raise ValueError(f"Unsupported asset_type: '{asset_type}'")
    return schema_cls.model_validate(data)
