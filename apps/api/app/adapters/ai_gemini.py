import json
import logging
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.adapters.base import AIExtractionResult, AIProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class ConfidentialDataBlockedError(PermissionError):
    """Raised when non-public / confidential data is submitted to a free-tier AI provider."""



class GeminiExtractionOutput(BaseModel):
    """Structured extraction output schema returned by Gemini."""

    suggested_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific dynamic metadata fields extracted from the text",
    )
    english_summary: str = Field(
        default="",
        description="Concise English executive summary of the document or media",
    )
    tenglish_keywords: list[str] = Field(
        default_factory=list,
        description="Phonetic Telugu written in Latin script (Tenglish) search keywords",
    )
    suggested_geo_names: list[str] = Field(
        default_factory=list,
        description="Names of geographic entities (districts, mandals, constituencies) mentioned",
    )
    confidence: float = 1.0


class GeminiAIProvider:
    """Gemini AI Provider with hard privacy guardrail for confidential documents."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        tier: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self.tier = (tier or settings.GEMINI_TIER).lower()
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "Gemini API key is not configured. Set GEMINI_API_KEY in environment or .env."
                )
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _build_prompt(self, text: str, asset_type: str) -> str:
        return f"""You are the Digital Intelligence Assistant for the JanaSena Party (JSP).
Analyze the following extracted document or media text of type '{asset_type}'.

Tasks:
1. suggested_metadata: Extract type-specific dynamic metadata dictionary according to the asset type:
   - government_document: go_number, issuing_department, date_of_issue, subject, state, district_local_body, related_scheme
   - newspaper_clipping: newspaper_name, publication_date, headline, edition, page_number
   - online_news_social: platform_publisher, source_url, published_date, author_handle, key_quote
   - video_audio: source_channel_event, recording_date, speakers (list of names), venue
   - image_infographic: event_subject, capture_date, credit_source, people_depicted, caption
   - research_material: document_title, authoring_body, publication_date, executive_summary
2. english_summary: A concise, objective 2-4 sentence executive summary in English.
3. tenglish_keywords: 5 to 10 phonetic Telugu search keywords written in the Latin alphabet (Tenglish), representing common Telugu search terms for this content (e.g. 'rythu', 'panta bima', 'polavaram', 'varahi yatra').
4. suggested_geo_names: Names of any Andhra Pradesh or Indian geographic entities mentioned (states, districts, assembly constituencies, mandals, villages, cities).

Document Text:
\"\"\"
{text[:15000]}
\"\"\"
"""

    def extract_document_intelligence(
        self,
        text_or_bytes: str | bytes,
        asset_type: str,
        is_public: bool,
    ) -> GeminiExtractionOutput:
        """Extract structured document intelligence while enforcing privacy guardrails."""
        # 1. HARD PRIVACY GUARDRAIL
        if not is_public and self.tier == "free":
            raise ConfidentialDataBlockedError(
                "Confidential documents cannot be processed by free-tier AI keys. "
                "Gemini Free Tier trains on inputs and violates confidential document privacy guardrails."
            )

        text = (
            text_or_bytes
            if isinstance(text_or_bytes, str)
            else text_or_bytes.decode(errors="ignore")
        )

        if not text.strip():
            return GeminiExtractionOutput(
                suggested_metadata={},
                english_summary="",
                tenglish_keywords=[],
                suggested_geo_names=[],
            )

        client = self._get_client()
        prompt = self._build_prompt(text=text, asset_type=asset_type)

        try:
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiExtractionOutput,
                ),
            )
            raw_text = response.text or "{}"
            data = json.loads(raw_text)
            return GeminiExtractionOutput.model_validate(data)
        except Exception as exc:
            # Rate limit or quota error handling - degrade gracefully
            err_str = str(exc).lower()
            if "429" in err_str or "resourceexhausted" in err_str or "quota" in err_str:
                logger.warning("Gemini rate limit / quota exceeded. Degrading gracefully: %s", exc)
                return GeminiExtractionOutput(
                    suggested_metadata={},
                    english_summary="AI extraction temporarily unavailable due to rate limits. Please review manually.",
                    tenglish_keywords=[],
                    suggested_geo_names=[],
                    confidence=0.0,
                )
            raise

    def extract_metadata_and_summary(
        self,
        text_or_bytes: str | bytes,
        asset_type: str,
        is_public: bool,
    ) -> AIExtractionResult:
        """Conform to the AIProvider Protocol."""
        output = self.extract_document_intelligence(
            text_or_bytes=text_or_bytes,
            asset_type=asset_type,
            is_public=is_public,
        )

        meta = output.suggested_metadata
        title = (
            meta.get("title")
            or meta.get("headline")
            or meta.get("subject")
            or meta.get("document_title")
            or None
        )

        return AIExtractionResult(
            title=title,
            summary=output.english_summary,
            tags=output.tenglish_keywords,
            entities=output.suggested_geo_names,
            confidence=output.confidence,
            raw_output={
                "suggested_metadata": output.suggested_metadata,
                "english_summary": output.english_summary,
                "tenglish_keywords": output.tenglish_keywords,
                "suggested_geo_names": output.suggested_geo_names,
            },
        )


# Static Protocol conformance check
_: type[AIProvider] = GeminiAIProvider
