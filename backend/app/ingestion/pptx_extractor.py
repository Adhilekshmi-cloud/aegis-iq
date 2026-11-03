"""Microsoft PowerPoint (.pptx) document extractor for Aegis Knowledge System."""

import logging
from pathlib import Path
from typing import Any, Dict, List

from app.ingestion.registry import ExtractionResult

try:
    import pptx
    _PPTX_AVAILABLE = True
except ImportError:
    _PPTX_AVAILABLE = False

logger = logging.getLogger(__name__)


class PPTXExtractor:
    """Extracts slide text, tables, slide titles, and speaker notes from PowerPoint presentations."""

    def can_handle(self, file_path: Path) -> bool:
        """Check if file has a .pptx extension."""
        return file_path.suffix.lower() in (".pptx", ".pptm")

    async def extract(self, file_path: Path) -> ExtractionResult:
        """Extract content from a PowerPoint presentation file.

        Args:
            file_path: Path to .pptx file.

        Returns:
            ExtractionResult instance.
        """
        if not file_path.exists():
            return ExtractionResult(
                text="",
                confidence=0.0,
                errors=[f"File does not exist: {file_path}"],
            )

        if not _PPTX_AVAILABLE:
            return ExtractionResult(
                text="",
                confidence=0.0,
                errors=["python-pptx is not installed."],
            )

        try:
            prs = pptx.Presentation(file_path)
        except Exception as exc:
            logger.error("Failed to open PPTX %s: %s", file_path.name, exc)
            return ExtractionResult(
                text="",
                confidence=0.0,
                errors=[f"Failed to open PPTX: {str(exc)}"],
            )

        slide_count = len(prs.slides)
        sections: List[Dict[str, Any]] = []
        tables: List[Dict[str, Any]] = []
        all_text_blocks: List[str] = []

        for slide_idx, slide in enumerate(prs.slides, start=1):
            slide_title = f"Slide {slide_idx}"
            slide_body_texts: List[str] = []

            # 1. Inspect shapes for titles, text frames, and tables
            for shape in slide.shapes:
                # Slide Title
                if shape.has_text_frame:
                    shape_text = shape.text_frame.text.strip()
                    if shape == slide.shapes.title and shape_text:
                        slide_title = shape_text
                    elif shape_text:
                        slide_body_texts.append(shape_text)

                # Slide Table
                if shape.has_table:
                    tbl = shape.table
                    tbl_rows: List[List[str]] = []
                    for row in tbl.rows:
                        row_vals = [cell.text.strip() for cell in row.cells]
                        tbl_rows.append(row_vals)

                    if len(tbl_rows) >= 2:
                        header_row = tbl_rows[0]
                        body_rows = tbl_rows[1:]
                        tables.append({
                            "headers": header_row,
                            "rows": body_rows,
                            "slide": slide_idx,
                        })

            # 2. Extract speaker notes
            notes_text = ""
            try:
                if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                    notes_text = slide.notes_slide.notes_text_frame.text.strip()
                    if notes_text:
                        slide_body_texts.append(f"Speaker Notes: {notes_text}")
            except Exception as note_exc:
                logger.debug("Slide %d notes note: %s", slide_idx, note_exc)

            combined_slide_content = "\n".join(slide_body_texts)
            sections.append({
                "heading": slide_title,
                "content": combined_slide_content,
                "page": slide_idx,
            })

            all_text_blocks.append(f"=== {slide_title} ===\n{combined_slide_content}")

        full_text = "\n\n".join(all_text_blocks)

        metadata = {
            "filename": file_path.name,
            "title": file_path.stem.replace("_", " ").title(),
            "slide_count": slide_count,
        }

        return ExtractionResult(
            text=full_text,
            tables=tables,
            metadata=metadata,
            sections=sections,
            images=[],
            extraction_method="python-pptx",
            confidence=0.98,
            errors=[],
            page_count=slide_count,
            raw_content=full_text,
        )
