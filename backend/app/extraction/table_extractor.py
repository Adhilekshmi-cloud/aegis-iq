"""Structured fact extraction from table data for Aegis Knowledge System.

Parses tabular data (from PDFs, HTML, Excel, Word), detects header structures,
extracts units from headers or cells, and converts rows into engineering facts.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.normalization.unit_normalizer import normalize_unit, parse_value_unit

logger = logging.getLogger(__name__)

# Regex to detect unit inside parenthesis or square brackets in header: e.g. "Pressure (PSI)"
_HEADER_UNIT_REGEX = re.compile(r"^(.*?)\s*[\(\[]([a-zA-Z°℃℉Ωµ%\/\*\-\^0-9\.]+)[\)\]]\s*$")


@dataclass
class RawTableFact:
    """An individual fact extracted from a table row or cell."""
    subject: str
    predicate: str
    value: str
    unit: Optional[str] = None
    numeric_value: Optional[float] = None
    tolerance_min: Optional[float] = None
    tolerance_max: Optional[float] = None
    raw_snippet: str = ""
    table_index: int = 0
    row_index: int = 0


def clean_header_text(header: Any) -> str:
    """Clean and standardize header string."""
    if header is None:
        return ""
    text = str(header).strip()
    return re.sub(r"\s+", " ", text)


def extract_header_and_unit(header: str) -> Tuple[str, Optional[str]]:
    """Extract predicate name and embedded unit from a table header.

    Examples:
        'Operating Pressure (PSI)' -> ('Operating Pressure', 'PSI')
        'Flow Rate [GPM]' -> ('Flow Rate', 'GPM')
        'Supply Voltage' -> ('Supply Voltage', None)

    Args:
        header: Column header text.

    Returns:
        Tuple of (clean_predicate_name, normalized_unit).
    """
    clean_h = clean_header_text(header)
    match = _HEADER_UNIT_REGEX.match(clean_h)
    if match:
        pred = match.group(1).strip()
        raw_u = match.group(2).strip()
        norm_u = normalize_unit(raw_u)
        return pred, norm_u
    return clean_h, None


class TableExtractor:
    """Extracts structured engineering facts from tabular structures."""

    def __init__(self, default_subject: str = "Aegis System"):
        """Initialize TableExtractor.

        Args:
            default_subject: Fallback subject if row doesn't specify component.
        """
        self.default_subject = default_subject

    def extract_facts_from_table(
        self,
        table_dict: Dict[str, Any],
        table_index: int = 0,
        page_number: Optional[int] = None,
        context_subject: Optional[str] = None,
    ) -> List[RawTableFact]:
        """Extract facts from a standardized table dict.

        Format:
        {
            "headers": ["Component", "Operating Pressure (PSI)", "Max Temp (°C)"],
            "rows": [
                ["PA-7100", "3000", "85"],
                ["SV-4200", "3150", "90"]
            ]
        }
        Or key-value vertical table:
        {
            "headers": ["Parameter", "Value", "Unit"],
            "rows": [
                ["Operating Pressure", "3000", "PSI"],
                ["Fluid Type", "MIL-PRF-83282", ""]
            ]
        }

        Args:
            table_dict: Dictionary containing 'headers' and 'rows'.
            table_index: Index of table within document.
            page_number: Document page number where table resides.
            context_subject: Section or document-level subject fallback.

        Returns:
            List of RawTableFact instances.
        """
        headers = table_dict.get("headers", [])
        rows = table_dict.get("rows", [])

        if not headers or not rows:
            return []

        clean_headers = [clean_header_text(h) for h in headers]
        facts: List[RawTableFact] = []

        # Detect table orientation:
        # Check if this is a Parameter-Value (key-value) vertical table
        first_h_lower = clean_headers[0].lower() if clean_headers else ""
        second_h_lower = clean_headers[1].lower() if len(clean_headers) > 1 else ""

        is_param_val_table = (
            ("param" in first_h_lower or "spec" in first_h_lower or "property" in first_h_lower or "item" in first_h_lower)
            and ("val" in second_h_lower or "spec" in second_h_lower or "setting" in second_h_lower or "requirement" in second_h_lower)
        )

        has_unit_column = False
        unit_col_idx = -1
        for idx, h in enumerate(clean_headers):
            if h.lower() in ("unit", "units", "dimension"):
                has_unit_column = True
                unit_col_idx = idx
                break

        if is_param_val_table:
            # Vertical format: Row 0 is [Predicate, Value, (optional Unit)]
            subject = context_subject or self.default_subject
            for r_idx, row in enumerate(rows):
                if not row or len(row) < 2:
                    continue
                pred = str(row[0]).strip()
                val_raw = str(row[1]).strip()
                if not pred or not val_raw:
                    continue

                col_unit = str(row[unit_col_idx]).strip() if has_unit_column and len(row) > unit_col_idx else None
                norm_col_unit = normalize_unit(col_unit)

                # Parse value and unit
                num_val, parsed_unit, formatted_val = parse_value_unit(val_raw)
                final_unit = norm_col_unit or parsed_unit

                snippet = f"{pred}: {val_raw}" + (f" {final_unit}" if final_unit and final_unit not in val_raw else "")
                facts.append(
                    RawTableFact(
                        subject=subject,
                        predicate=pred,
                        value=formatted_val if num_val is not None else val_raw,
                        unit=final_unit,
                        numeric_value=num_val,
                        raw_snippet=snippet,
                        table_index=table_index,
                        row_index=r_idx,
                    )
                )
            return facts

        # Horizontal format: Column 0 is Subject or Component, remaining columns are Predicates
        # e.g. ["Component", "Pressure (PSI)", "Flow (GPM)"]
        parsed_col_info = [extract_header_and_unit(h) for h in clean_headers]

        subject_col_idx = 0
        for r_idx, row in enumerate(rows):
            if not row:
                continue

            row_subject = str(row[subject_col_idx]).strip() if len(row) > subject_col_idx else ""
            if not row_subject:
                row_subject = context_subject or self.default_subject

            for c_idx in range(1, len(clean_headers)):
                if c_idx >= len(row):
                    continue
                cell_raw = str(row[c_idx]).strip()
                if not cell_raw or cell_raw.lower() in ("-", "n/a", "none", "null"):
                    continue

                pred_name, header_unit = parsed_col_info[c_idx]
                num_val, cell_unit, formatted_val = parse_value_unit(cell_raw)
                final_unit = header_unit or cell_unit

                snippet = f"{row_subject} | {pred_name}: {cell_raw}" + (
                    f" {final_unit}" if final_unit and final_unit not in cell_raw else ""
                )

                facts.append(
                    RawTableFact(
                        subject=row_subject,
                        predicate=pred_name,
                        value=formatted_val if num_val is not None else cell_raw,
                        unit=final_unit,
                        numeric_value=num_val,
                        raw_snippet=snippet,
                        table_index=table_index,
                        row_index=r_idx,
                    )
                )

        logger.debug("Extracted %d facts from table %d", len(facts), table_index)
        return facts
