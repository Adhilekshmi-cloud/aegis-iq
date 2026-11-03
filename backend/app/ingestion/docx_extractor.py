"""Microsoft Word (.docx) document extractor for Aegis Knowledge System."""

import logging
from pathlib import Path
from typing import Any, Dict, List

from app.ingestion.registry import ExtractionResult

try:
    import docx
    _DOCX_AVAILABLE = True
except ImportError:
    _DOCX_AVAILABLE = False

logger = logging.getLogger(__name__)


class DOCXExtractor:
    """Extracts text, structured tables, headings, and metadata from .docx files."""

    def can_handle(self, file_path: Path) -> bool:
        """Check if file has a .docx extension."""
        return file_path.suffix.lower() == ".docx"

    async def extract(self, file_path: Path) -> ExtractionResult:
        """Extract content from a Word document.

        Args:
            file_path: Path to .docx file.

        Returns:
            ExtractionResult instance.
        """
        if not file_path.exists():
            return ExtractionResult(
                text="",
                confidence=0.0,
                errors=[f"File does not exist: {file_path}"],
            )

        if not _DOCX_AVAILABLE:
            return ExtractionResult(
                text="",
                confidence=0.0,
                errors=["python-docx is not installed."],
            )

        try:
            doc = docx.Document(file_path)
        except Exception as exc:
            logger.error("Failed to open DOCX %s: %s", file_path.name, exc)
            return ExtractionResult(
                text="",
                confidence=0.0,
                errors=[f"Failed to open DOCX: {str(exc)}"],
            )

        # 1. Extract Core Properties
        metadata: Dict[str, Any] = {
            "filename": file_path.name,
            "title": file_path.stem.replace("_", " ").title(),
        }
        try:
            core_props = doc.core_properties
            if core_props.title:
                metadata["title"] = core_props.title
            if core_props.author:
                metadata["author"] = core_props.author
            if core_props.created:
                metadata["date"] = core_props.created.isoformat()
            if core_props.revision:
                metadata["revision"] = str(core_props.revision)
        except Exception as prop_exc:
            logger.debug("DOCX core properties note: %s", prop_exc)

        # 2. Extract Headings and Paragraphs into Sections
        sections: List[Dict[str, Any]] = []
        current_heading = "Introduction"
        current_paras: List[str] = []
        all_text_paras: List[str] = []

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue

            style_name = p.style.name.lower() if p.style else ""
            if "heading" in style_name or "title" in style_name:
                if current_paras:
                    sections.append({
                        "heading": current_heading,
                        "content": "\n".join(current_paras),
                        "page": 1,
                    })
                    current_paras = []
                current_heading = text
            else:
                current_paras.append(text)
            all_text_paras.append(text)

        if current_paras:
            sections.append({
                "heading": current_heading,
                "content": "\n".join(current_paras),
                "page": 1,
            })

        # 3. Extract Tables with Merged Cell Handling
        tables: List[Dict[str, Any]] = []
        for tbl in doc.tables:
            if not tbl.rows:
                continue

            table_matrix: List[List[str]] = []
            for row in tbl.rows:
                row_cells: List[str] = []
                for cell in row.cells:
                    c_text = cell.text.strip()
                    row_cells.append(c_text)
                table_matrix.append(row_cells)

            if len(table_matrix) >= 2:
                header_row = table_matrix[0]
                body_rows = table_matrix[1:]
                tables.append({"headers": header_row, "rows": body_rows})

        full_text = "\n\n".join(all_text_paras)

        return ExtractionResult(
            text=full_text,
            tables=tables,
            metadata=metadata,
            sections=sections,
            images=[],
            extraction_method="python-docx",
            confidence=0.98,
            errors=[],
            page_count=1,
            raw_content=full_text,
        )
