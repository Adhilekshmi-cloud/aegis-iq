"""OCR document extractor using Tesseract and Pillow for scanned documents and images."""

import logging
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from app.ingestion.registry import ExtractionResult

try:
    import pytesseract
    _PYTESSERACT_AVAILABLE = True
except ImportError:
    _PYTESSERACT_AVAILABLE = False

logger = logging.getLogger(__name__)


def preprocess_image_for_ocr(img: Image.Image) -> Image.Image:
    """Preprocess image to maximize OCR text recognition accuracy.

    Applies grayscale conversion, contrast enhancement, median denoising, and thresholding.

    Args:
        img: Input PIL Image.

    Returns:
        Enhanced PIL Image ready for Tesseract OCR.
    """
    # 1. Convert to grayscale
    gray = img.convert("L")

    # 2. Increase contrast
    enhancer = ImageEnhance.Contrast(gray)
    enhanced = enhancer.enhance(1.8)

    # 3. Median filter to remove salt-and-pepper noise
    denoised = enhanced.filter(ImageFilter.MedianFilter(size=3))

    # 4. Otsu-like thresholding or standard binarization
    threshold = 140
    binarized = denoised.point(lambda p: 255 if p > threshold else 0)

    return binarized


class OCRExtractor:
    """Optical Character Recognition extractor for scanned documents, PDFs, and images."""

    def __init__(self, tesseract_cmd: Optional[str] = None):
        """Initialize OCRExtractor.

        Args:
            tesseract_cmd: Optional explicit path to the tesseract executable.
        """
        if tesseract_cmd and _PYTESSERACT_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def can_handle(self, file_path: Path) -> bool:
        """Check if file can be handled by OCR (images and scanned PDFs)."""
        suffix = file_path.suffix.lower()
        return suffix in (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".tif")

    def is_tesseract_installed(self) -> bool:
        """Verify whether Tesseract binary is accessible and operational."""
        if not _PYTESSERACT_AVAILABLE:
            return False
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def ocr_pil_image(self, img: Image.Image) -> Tuple[str, float, List[str]]:
        """Run OCR on a PIL image with confidence reporting.

        Args:
            img: PIL Image object.

        Returns:
            Tuple of (extracted_text, average_confidence, errors_list).
        """
        if not _PYTESSERACT_AVAILABLE:
            return "", 0.0, ["pytesseract module is not installed."]

        if not self.is_tesseract_installed():
            return "", 0.0, ["Tesseract OCR engine is not installed or not in PATH."]

        try:
            processed = preprocess_image_for_ocr(img)

            # Get detailed OCR data including word confidences
            ocr_data = pytesseract.image_to_data(
                processed, output_type=pytesseract.Output.DICT
            )

            texts: List[str] = []
            confidences: List[float] = []

            for i in range(len(ocr_data["text"])):
                word = ocr_data["text"][i].strip()
                conf = float(ocr_data["conf"][i])
                if word and conf > 0:
                    texts.append(word)
                    confidences.append(conf / 100.0)

            full_text = pytesseract.image_to_string(processed).strip()
            avg_conf = (sum(confidences) / len(confidences)) if confidences else 0.5
            return full_text, round(avg_conf, 2), []

        except Exception as exc:
            logger.error("OCR execution failed: %s", exc)
            return "", 0.0, [f"OCR error: {str(exc)}"]

    async def extract(self, file_path: Path) -> ExtractionResult:
        """Extract text and metadata from an image or scanned document file.

        Args:
            file_path: Path to file.

        Returns:
            ExtractionResult instance.
        """
        if not file_path.exists():
            return ExtractionResult(
                text="",
                confidence=0.0,
                errors=[f"File not found: {file_path}"],
            )

        try:
            with Image.open(file_path) as img:
                text, conf, errors = self.ocr_pil_image(img)
                return ExtractionResult(
                    text=text,
                    tables=[],
                    metadata={
                        "filename": file_path.name,
                        "format": img.format,
                        "size": f"{img.width}x{img.height}",
                    },
                    sections=[{"heading": file_path.stem, "content": text, "page": 1}],
                    images=[{"description": f"Scanned image {file_path.name}", "page": 1}],
                    extraction_method="ocr",
                    confidence=conf,
                    errors=errors,
                    page_count=1,
                    raw_content=text,
                )
        except Exception as exc:
            logger.error("Failed to extract image via OCR from %s: %s", file_path.name, exc)
            return ExtractionResult(
                text="",
                confidence=0.0,
                errors=[f"Failed to open/process image: {str(exc)}"],
            )
