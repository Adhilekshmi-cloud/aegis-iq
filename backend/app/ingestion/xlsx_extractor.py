"""Microsoft Excel (.xlsx) document extractor for Aegis Knowledge System."""

import logging
from pathlib import Path
from typing import Any, Dict, List

from app.ingestion.registry import ExtractionResult

try:
    import openpyxl
    _OPENPYXL_AVAILABLE = True
except ImportError:
    _OPENPYXL_AVAILABLE = False

logger = logging.getLogger(__name__)


class XLSXExtractor:
    """Extracts worksheets, structured tables, and merged cell values from Excel workbooks."""

    def can_handle(self, file_path: Path) -> bool:
        """Check if file has an Excel extension."""
        return file_path.suffix.lower() in (".xlsx", ".xlsm", ".xltx")

    async def extract(self, file_path: Path) -> ExtractionResult:
        """Extract content from an Excel workbook.

        Args:
            file_path: Path to .xlsx file.

        Returns:
            ExtractionResult instance.
        """
        if not file_path.exists():
            return ExtractionResult(
                text="",
                confidence=0.0,
                errors=[f"File does not exist: {file_path}"],
            )

        if not _OPENPYXL_AVAILABLE:
            return ExtractionResult(
                text="",
                confidence=0.0,
                errors=["openpyxl is not installed."],
            )

        try:
            # Load workbook with data_only=True to evaluate formulas to values
            wb = openpyxl.load_workbook(file_path, data_only=True)
        except Exception as exc:
            logger.error("Failed to load Excel workbook %s: %s", file_path.name, exc)
            return ExtractionResult(
                text="",
                confidence=0.0,
                errors=[f"Failed to open Excel workbook: {str(exc)}"],
            )

        tables: List[Dict[str, Any]] = []
        sections: List[Dict[str, Any]] = []
        full_text_lines: List[str] = []

        for sheet_idx, sheet_name in enumerate(wb.sheetnames):
            sheet = wb[sheet_name]
            rows_data: List[List[str]] = []

            # Resolve merged cells map (coord -> top_left_value)
            merged_values: Dict[str, Any] = {}
            for rng in sheet.merged_cells.ranges:
                top_left_cell = sheet.cell(rng.min_row, rng.min_col)
                top_left_val = top_left_cell.value
                for row_idx in range(rng.min_row, rng.max_row + 1):
                    for col_idx in range(rng.min_col, rng.max_col + 1):
                        coord = f"{row_idx}:{col_idx}"
                        merged_values[coord] = top_left_val

            for r_idx, row in enumerate(sheet.iter_rows(values_only=False), start=1):
                row_vals: List[str] = []
                has_content = False
                for c_idx, cell in enumerate(row, start=1):
                    coord = f"{r_idx}:{c_idx}"
                    val = merged_values.get(coord, cell.value)
                    if val is not None:
                        val_str = str(val).strip()
                        row_vals.append(val_str)
                        if val_str:
                            has_content = True
                    else:
                        row_vals.append("")

                if has_content:
                    rows_data.append(row_vals)

            if not rows_data:
                continue

            # First row with content is header
            header_row = rows_data[0]
            body_rows = rows_data[1:]

            if header_row and body_rows:
                tables.append({
                    "headers": header_row,
                    "rows": body_rows,
                    "sheet": sheet_name,
                })

            # Format sheet text
            sheet_text_lines = [f"=== Sheet: {sheet_name} ==="]
            sheet_text_lines.append(" | ".join(header_row))
            for r in body_rows:
                sheet_text_lines.append(" | ".join(r))

            sheet_content = "\n".join(sheet_text_lines)
            sections.append({
                "heading": f"Sheet: {sheet_name}",
                "content": sheet_content,
                "page": sheet_idx + 1,
            })
            full_text_lines.append(sheet_content)

        wb.close()
        full_text = "\n\n".join(full_text_lines)

        metadata = {
            "filename": file_path.name,
            "title": file_path.stem.replace("_", " ").title(),
            "sheets": wb.sheetnames if hasattr(wb, "sheetnames") else [],
        }

        return ExtractionResult(
            text=full_text,
            tables=tables,
            metadata=metadata,
            sections=sections,
            images=[],
            extraction_method="openpyxl",
            confidence=0.98,
            errors=[],
            page_count=len(wb.sheetnames) if hasattr(wb, "sheetnames") else 1,
            raw_content=full_text,
        )
