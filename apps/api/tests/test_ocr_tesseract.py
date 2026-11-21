import io
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image, ImageDraw

from app.adapters.base import OCRProvider, OCRResult
from app.adapters.ocr_tesseract import TesseractOCRProvider
from app.adapters.registry import get_ocr_provider


def _create_sample_pdf_bytes(page_texts: list[str]) -> bytes:
    """Create an in-memory multi-page PDF using PIL."""
    images: list[Image.Image] = []
    for text in page_texts:
        img = Image.new("RGB", (400, 150), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((20, 40), text, fill=(0, 0, 0))
        images.append(img)

    buf = io.BytesIO()
    images[0].save(buf, format="PDF", save_all=True, append_images=images[1:])
    return buf.getvalue()


def _create_sample_image_bytes(text: str) -> bytes:
    """Create an in-memory single image (JPEG)."""
    img = Image.new("RGB", (300, 100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 30), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_tesseract_ocr_provider_conforms_to_protocol() -> None:
    provider = TesseractOCRProvider()
    assert isinstance(provider, OCRProvider)


def test_registry_selects_tesseract_provider() -> None:
    provider = get_ocr_provider("tesseract")
    assert isinstance(provider, TesseractOCRProvider)

    # Alias check
    alias_provider = get_ocr_provider("pytesseract")
    assert isinstance(alias_provider, TesseractOCRProvider)


def test_missing_binary_raises_descriptive_error() -> None:
    provider = TesseractOCRProvider(tesseract_cmd="/nonexistent/bin/tesseract")
    with pytest.raises(RuntimeError) as exc_info:
        provider.check_prerequisites(["eng", "tel"])
    assert "Tesseract OCR binary not found" in str(exc_info.value)


@patch("shutil.which", return_value="/usr/local/bin/tesseract")
@patch("pytesseract.get_languages", return_value=["eng", "osd"])
def test_missing_telugu_pack_raises_descriptive_error(
    mock_get_languages: MagicMock, mock_which: MagicMock
) -> None:
    provider = TesseractOCRProvider(tesseract_cmd="tesseract")
    with pytest.raises(RuntimeError) as exc_info:
        provider.check_prerequisites(["eng", "tel"])
    assert "Tesseract Telugu language pack ('tel') not found" in str(exc_info.value)


@patch("shutil.which", return_value="/usr/local/bin/tesseract")
@patch("pytesseract.get_languages", return_value=["eng", "hin"])
def test_missing_other_pack_raises_descriptive_error(
    mock_get_languages: MagicMock, mock_which: MagicMock
) -> None:
    provider = TesseractOCRProvider(tesseract_cmd="tesseract")
    with pytest.raises(RuntimeError) as exc_info:
        provider.check_prerequisites(["eng", "fra"])
    assert "language pack 'fra' not found" in str(exc_info.value)


@patch.object(TesseractOCRProvider, "check_prerequisites")
@patch("pytesseract.image_to_string")
@patch("pytesseract.image_to_data")
def test_multipage_pdf_concatenation_and_lang_invocation(
    mock_image_to_data: MagicMock,
    mock_image_to_string: MagicMock,
    mock_check_prereqs: MagicMock,
) -> None:
    provider = TesseractOCRProvider()
    pdf_bytes = _create_sample_pdf_bytes(["Page 1: GO MS 104 Revenue", "Page 2: Allotment Schedule"])

    # Mock per-page string outputs
    mock_image_to_string.side_effect = [
        "Page 1: GO MS 104 Revenue",
        "Page 2: Allotment Schedule",
    ]
    # Mock image_to_data outputs with bounding boxes & confidences
    mock_image_to_data.side_effect = [
        {
            "text": ["Page", "1:", "GO"],
            "left": [20, 60, 80],
            "top": [40, 40, 40],
            "width": [35, 15, 25],
            "height": [12, 12, 12],
            "conf": [95, 96, 98],
        },
        {
            "text": ["Page", "2:", "Allotment"],
            "left": [20, 60, 80],
            "top": [40, 40, 40],
            "width": [35, 15, 60],
            "height": [12, 12, 12],
            "conf": [92, 94, 95],
        },
    ]

    result = provider.extract_text(pdf_bytes, mime_type="application/pdf", languages=["eng", "tel"])

    # Verify prerequisites checked with 'eng' and 'tel'
    mock_check_prereqs.assert_called_once_with(["eng", "tel"])

    # Verify image_to_string called twice with lang='eng+tel'
    assert mock_image_to_string.call_count == 2
    for call in mock_image_to_string.call_args_list:
        assert call.kwargs.get("lang") == "eng+tel"

    # Verify result structure
    assert isinstance(result, OCRResult)
    assert len(result.pages) == 2
    assert result.pages[0].page_number == 1
    assert result.pages[0].text == "Page 1: GO MS 104 Revenue"
    assert result.pages[0].confidence is not None
    assert result.pages[1].page_number == 2
    assert result.pages[1].text == "Page 2: Allotment Schedule"

    # Verify full text is concatenated with double newline
    expected_full = "Page 1: GO MS 104 Revenue\n\nPage 2: Allotment Schedule"
    assert result.full_text == expected_full

    # Verify layout boxes JSON
    assert "pages" in result.boxes_json
    assert len(result.boxes_json["pages"]) == 2
    assert len(result.boxes_json["pages"][0]["words"]) == 3


@patch.object(TesseractOCRProvider, "check_prerequisites")
@patch("pytesseract.image_to_string", return_value="Telugu Clipping: Eenadu News")
@patch("pytesseract.image_to_data")
def test_single_image_extraction(
    mock_image_to_data: MagicMock,
    mock_image_to_string: MagicMock,
    mock_check_prereqs: MagicMock,
) -> None:
    provider = TesseractOCRProvider()
    img_bytes = _create_sample_image_bytes("Eenadu News")
    mock_image_to_data.return_value = {
        "text": ["Eenadu", "News"],
        "left": [10, 70],
        "top": [30, 30],
        "width": [50, 40],
        "height": [15, 15],
        "conf": [90, 92],
    }

    result = provider.extract_text(img_bytes, mime_type="image/jpeg", languages=["tel", "eng"])

    assert mock_image_to_string.call_count == 1
    assert mock_image_to_string.call_args.kwargs.get("lang") == "tel+eng"
    assert len(result.pages) == 1
    assert result.pages[0].page_number == 1
    assert result.pages[0].text == "Telugu Clipping: Eenadu News"
    assert result.full_text == "Telugu Clipping: Eenadu News"


@patch.object(TesseractOCRProvider, "check_prerequisites")
@patch("pytesseract.image_to_string", return_value="Sample Text")
@patch("pytesseract.image_to_data", return_value={"text": ["Sample"], "left": [0], "top": [0], "width": [10], "height": [10], "conf": [90]})
def test_max_pdf_pages_capping(
    mock_image_to_data: MagicMock,
    mock_image_to_string: MagicMock,
    mock_check_prereqs: MagicMock,
) -> None:
    provider = TesseractOCRProvider(max_pdf_pages=2)
    # 4-page PDF
    pdf_bytes = _create_sample_pdf_bytes(["P1", "P2", "P3", "P4"])

    result = provider.extract_text(pdf_bytes, mime_type="application/pdf")

    # Only 2 pages processed because of max_pdf_pages cap
    assert len(result.pages) == 2
    assert mock_image_to_string.call_count == 2


def test_real_tesseract_ocr_extraction_if_available() -> None:
    provider = TesseractOCRProvider()
    try:
        provider.check_prerequisites(["eng", "tel"])
    except RuntimeError:
        pytest.skip("Tesseract or telugu language pack not available in test environment")

    # Real image with bold printed text
    img = Image.new("RGB", (400, 100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 30), "JSP DIGITAL INTELLIGENCE", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    result = provider.extract_text(buf.getvalue(), mime_type="image/png", languages=["eng", "tel"])
    assert isinstance(result, OCRResult)
    assert len(result.pages) == 1
    assert "DIGITAL" in result.full_text or "INTELLIGENCE" in result.full_text or "JSP" in result.full_text

