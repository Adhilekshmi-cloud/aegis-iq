"""PDF document extractor using PyMuPDF (fitz) with automatic scanned document fallback."""

import io
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image

from app.ingestion.ocr_extractor import OCRExtractor
from app.ingestion.registry import ExtractionResult

try:
    import fitz  # PyMuPDF
    _FITZ_AVAILABLE = True
except ImportError:
    _FITZ_AVAILABLE = False

logger = logging.getLogger(__name__)

SCANNED_THRESHOLD_CHARS_PER_PAGE = 50


class PDFExtractor:
    """Born-digital and scanned PDF extractor powered by PyMuPDF and OCR."""

    def __init__(self, ocr_extractor: Optional[OCRExtractor] = None):
        """Initialize PDFExtractor with optional OCR extractor."""
        self.ocr_extractor = ocr_extractor or OCRExtractor()

    def can_handle(self, file_path: Path) -> bool:
        """Check if file has a .pdf extension."""
        return file_path.suffix.lower() == ".pdf"

    async def extract(self, file_path: Path) -> ExtractionResult:
        """Extract text, tables, sections, and metadata from a PDF file.

        Args:
            file_path: Path to target PDF file.

        Returns:
            ExtractionResult.
        """
        if not file_path.exists():
            return ExtractionResult(
                text="",
                confidence=0.0,
                errors=[f"File does not exist: {file_path}"],
            )

        if not _FITZ_AVAILABLE:
            return ExtractionResult(
                text="",
                confidence=0.0,
                errors=["PyMuPDF (fitz) is not installed."],
            )

        try:
            doc = fitz.open(file_path)
        except Exception as exc:
            logger.error("Failed to open PDF %s: %s", file_path.name, exc)
            return ExtractionResult(
                text="",
                confidence=0.0,
                errors=[f"Error opening PDF: {str(exc)}"],
            )

        page_count = len(doc)
        all_text_parts: List[str] = []
        tables: List[Dict[str, Any]] = []
        sections: List[Dict[str, Any]] = []
        images: List[Dict[str, Any]] = []
        errors: List[str] = []

        # Read native PDF metadata
        pdf_meta = doc.metadata or {}
        metadata: Dict[str, Any] = {
            "title": pdf_meta.get("title") or file_path.stem.replace("_", " ").title(),
            "author": pdf_meta.get("author") or "",
            "date": pdf_meta.get("creationDate") or "",
            "subject": pdf_meta.get("subject") or "",
            "page_count": page_count,
        }

        total_extracted_chars = 0
        is_scanned = False
        method = "pymupdf"
        confidence = 0.98

        # First pass: try extracting native text from pages
        page_texts: List[str] = []
        for page_idx in range(page_count):
            page = doc[page_idx]
            page_num = page_idx + 1

            # Extract native text
            p_text = page.get_text("text").strip()
            page_texts.append(p_text)
            total_extracted_chars += len(p_text)

            # Try PyMuPDF table extraction if supported
            try:
                table_finder = page.find_tables()
                if table_finder and table_finder.tables:
                    for tbl in table_finder.tables:
                        extracted_df = tbl.extract()
                        if extracted_df and len(extracted_df) >= 2:
                            header_row = [str(c or "").strip() for c in extracted_df[0]]
                            body_rows = [
                                [str(c or "").strip() for c in row]
                                for row in extracted_df[1:]
                            ]
                            tables.append({"headers": header_row, "rows": body_rows})
            except Exception as tbl_exc:
                logger.debug("PyMuPDF table extraction note on page %d: %s", page_num, tbl_exc)

        # Detect if PDF is scanned
        avg_chars = total_extracted_chars / max(1, page_count)
        if avg_chars < SCANNED_THRESHOLD_CHARS_PER_PAGE:
            is_scanned = True
            logger.info("PDF %s detected as scanned (avg %.1f chars/page). Running OCR...", file_path.name, avg_chars)
            method = "ocr"
            confidence = 0.85

            # Run OCR on each page raster
            page_texts = []
            for page_idx in range(page_count):
                page = doc[page_idx]
                page_num = page_idx + 1
                try:
                    # Render page to pixmap
                    pix = page.get_pixmap(dpi=200)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    ocr_text, ocr_conf, ocr_errs = self.ocr_extractor.ocr_pil_image(img)
                    if ocr_errs:
                        errors.extend(ocr_errs)
                    page_texts.append(ocr_text)
                except Exception as page_ocr_exc:
                    errors.append(f"Page {page_num} OCR error: {str(page_ocr_exc)}")
                    page_texts.append("")

        # Build sections and full text
        for page_idx, p_text in enumerate(page_texts):
            page_num = page_idx + 1
            if p_text:
                all_text_parts.append(f"--- Page {page_num} ---\n{p_text}")
                # Create section for each page
                sections.append({
                    "heading": f"Page {page_num}",
                    "content": p_text,
                    "page": page_num,
                })

        doc.close()

        full_text = "\n\n".join(all_text_parts)
        metadata["is_scanned"] = is_scanned

        return ExtractionResult(
            text=full_text,
            tables=tables,
            metadata=metadata,
            sections=sections,
            images=images,
            extraction_method=method,
            confidence=confidence,
            errors=errors,
            page_count=page_count,
            raw_content=full_text,
        )
