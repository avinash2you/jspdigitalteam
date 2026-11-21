import io
import shutil
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium
import pytesseract
from PIL import Image

from app.adapters.base import OCRPage, OCRProvider, OCRResult
from app.core.config import settings


class TesseractOCRProvider:
    """Tesseract OCR provider extracting English and Telugu text from images and PDFs."""

    def __init__(
        self,
        tesseract_cmd: str | None = None,
        tessdata_dir: str | None = None,
        max_pdf_pages: int = 50,
    ) -> None:
        if tesseract_cmd:
            self.tesseract_cmd = tesseract_cmd
        else:
            configured = getattr(settings, "TESSERACT_CMD", "tesseract")
            if shutil.which(configured):
                self.tesseract_cmd = configured
            elif Path("/opt/homebrew/bin/tesseract").is_file():
                self.tesseract_cmd = "/opt/homebrew/bin/tesseract"
            elif Path("/usr/bin/tesseract").is_file():
                self.tesseract_cmd = "/usr/bin/tesseract"
            else:
                self.tesseract_cmd = configured

        self.tessdata_dir = tessdata_dir or getattr(settings, "TESSDATA_PREFIX", None)
        self.max_pdf_pages = max_pdf_pages

    def _get_config(self) -> str:
        if self.tessdata_dir:
            return f"--tessdata-dir {self.tessdata_dir}"
        return ""

    def check_prerequisites(self, languages: list[str]) -> None:
        """Verify that the Tesseract binary and required language packs are available."""
        # 1. Verify Tesseract executable
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

        resolved_cmd = shutil.which(self.tesseract_cmd) or (
            self.tesseract_cmd if Path(self.tesseract_cmd).is_file() else None
        )
        if not resolved_cmd:
            raise RuntimeError(
                f"Tesseract OCR binary not found at '{self.tesseract_cmd}'. "
                "Please install Tesseract (e.g. 'brew install tesseract' or 'apt-get install tesseract-ocr')."
            )

        # 2. Verify language packs (Telugu & English)
        try:
            available_langs = pytesseract.get_languages(config=self._get_config())
        except Exception as exc:
            raise RuntimeError(
                f"Failed to query installed Tesseract languages: {exc}. "
                "Ensure Tesseract and tessdata are correctly installed."
            ) from exc

        for lang in languages:
            if lang not in available_langs:
                if lang == "tel":
                    raise RuntimeError(
                        "Tesseract Telugu language pack ('tel') not found in tessdata. "
                        "Please install Telugu.traineddata (e.g. 'brew install tesseract-lang' "
                        "or 'apt-get install tesseract-ocr-tel')."
                    )
                raise RuntimeError(
                    f"Tesseract language pack '{lang}' not found in tessdata. "
                    f"Available languages: {available_langs}"
                )

    def _rasterize_pages(
        self, file_bytes: bytes, mime_type: str
    ) -> list[tuple[int, Image.Image]]:
        """Rasterize PDF pages or extract image frames into PIL Images."""
        is_pdf = mime_type == "application/pdf" or file_bytes.startswith(b"%PDF")
        images: list[tuple[int, Image.Image]] = []

        if is_pdf:
            pdf = pdfium.PdfDocument(file_bytes)
            total_pages = len(pdf)
            pages_to_process = min(total_pages, self.max_pdf_pages)
            for idx in range(pages_to_process):
                page = pdf.get_page(idx)
                # Render at 2.0x scale (144 DPI) for OCR accuracy
                pil_img = page.render(scale=2.0).to_pil().convert("RGB")
                images.append((idx + 1, pil_img))
        else:
            img = Image.open(io.BytesIO(file_bytes))
            n_frames = getattr(img, "n_frames", 1)
            frames_to_process = min(n_frames, self.max_pdf_pages)
            for idx in range(frames_to_process):
                img.seek(idx)
                images.append((idx + 1, img.copy().convert("RGB")))

        return images

    def extract_text(
        self,
        file_bytes: bytes,
        mime_type: str,
        languages: list[str] | None = None,
    ) -> OCRResult:
        """Extract multi-lingual text and layout bounding boxes from document or image."""
        langs = languages or ["eng", "tel"]
        self.check_prerequisites(langs)

        images = self._rasterize_pages(file_bytes=file_bytes, mime_type=mime_type)
        if not images:
            return OCRResult(full_text="", pages=[], boxes_json={})

        lang_str = "+".join(langs)
        tess_config = self._get_config()

        ocr_pages: list[OCRPage] = []
        all_boxes: list[dict[str, Any]] = []

        for page_num, pil_img in images:
            text = pytesseract.image_to_string(pil_img, lang=lang_str, config=tess_config)

            # Extract layout data / bounding boxes & confidence scores
            data = pytesseract.image_to_data(
                pil_img, lang=lang_str, config=tess_config, output_type=pytesseract.Output.DICT
            )

            confidences: list[float] = []
            words: list[dict[str, Any]] = []
            n_boxes = len(data.get("text", []))

            for b_idx in range(n_boxes):
                raw_conf = data.get("conf", [])[b_idx]
                try:
                    conf_val = float(raw_conf)
                    if conf_val >= 0:
                        confidences.append(conf_val)
                except (ValueError, TypeError):
                    pass

                word = str(data.get("text", [])[b_idx]).strip()
                if word:
                    words.append(
                        {
                            "word": word,
                            "bbox": [
                                data["left"][b_idx],
                                data["top"][b_idx],
                                data["width"][b_idx],
                                data["height"][b_idx],
                            ],
                            "conf": data["conf"][b_idx],
                        }
                    )

            avg_conf = (
                round(sum(confidences) / len(confidences) / 100.0, 4) if confidences else None
            )
            ocr_pages.append(OCRPage(page_number=page_num, text=text.strip(), confidence=avg_conf))
            all_boxes.append({"page_number": page_num, "words": words})

        full_text = "\n\n".join(p.text for p in ocr_pages if p.text)
        return OCRResult(
            full_text=full_text,
            pages=ocr_pages,
            boxes_json={"pages": all_boxes},
        )


# Ensure static conformance to OCRProvider Protocol
_: type[OCRProvider] = TesseractOCRProvider
