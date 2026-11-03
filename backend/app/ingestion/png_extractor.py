"""PNG and image document extractor using OCR for Aegis Knowledge System."""

import logging
from pathlib import Path
from typing import Optional

from PIL import Image

from app.ingestion.ocr_extractor import OCRExtractor
from app.ingestion.registry import ExtractionResult

logger = logging.getLogger(__name__)


class PNGExtractor:
    """Extracts text and technical metadata from PNG and other image files using OCR."""

    def __init__(self, ocr_extractor: Optional[OCRExtractor] = None):
        """Initialize PNGExtractor with optional OCRExtractor."""
        self.ocr_extractor = ocr_extractor or OCRExtractor()

    def can_handle(self, file_path: Path) -> bool:
        """Check if file has an image extension (PNG, JPG, TIFF, etc.)."""
        return file_path.suffix.lower() in (".png", ".jpg", ".jpeg", ".tiff", ".bmp")

    async def extract(self, file_path: Path) -> ExtractionResult:
        """Extract content from an image file using OCR.

        Args:
            file_path: Path to image file.

        Returns:
            ExtractionResult instance.
        """
        if not file_path.exists():
            return ExtractionResult(
                text="",
                confidence=0.0,
                errors=[f"File does not exist: {file_path}"],
            )

        try:
            with Image.open(file_path) as img:
                img_width, img_height = img.size
                img_format = img.format or "PNG"

                # Check if Tesseract is available
                if not self.ocr_extractor.is_tesseract_installed():
                    logger.warning(
                        "Tesseract OCR is not installed. Unable to extract text from %s",
                        file_path.name,
                    )
                    return ExtractionResult(
                        text="",
                        tables=[],
                        metadata={
                            "filename": file_path.name,
                            "width": img_width,
                            "height": img_height,
                            "format": img_format,
                            "title": file_path.stem.replace("_", " ").title(),
                        },
                        sections=[],
                        images=[{
                            "description": f"Image file {file_path.name} ({img_width}x{img_height})",
                            "page": 1,
                        }],
                        extraction_method="image_metadata",
                        confidence=0.3,
                        errors=["Tesseract OCR engine is not installed or not in PATH."],
                        page_count=1,
                        raw_content="",
                    )

                text, conf, errors = self.ocr_extractor.ocr_pil_image(img)

                return ExtractionResult(
                    text=text,
                    tables=[],
                    metadata={
                        "filename": file_path.name,
                        "width": img_width,
                        "height": img_height,
                        "format": img_format,
                        "title": file_path.stem.replace("_", " ").title(),
                    },
                    sections=[{
                        "heading": file_path.stem.replace("_", " ").title(),
                        "content": text,
                        "page": 1,
                    }],
                    images=[{
                        "description": f"OCR-extracted image {file_path.name}",
                        "page": 1,
                    }],
                    extraction_method="ocr",
                    confidence=conf,
                    errors=errors,
                    page_count=1,
                    raw_content=text,
                )
        except Exception as exc:
            logger.error("Failed to extract image %s: %s", file_path.name, exc)
            return ExtractionResult(
                text="",
                confidence=0.0,
                errors=[f"Image extraction error: {str(exc)}"],
            )
