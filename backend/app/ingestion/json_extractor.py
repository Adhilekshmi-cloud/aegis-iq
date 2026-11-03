"""Native JSON document extractor for Aegis Knowledge System."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.ingestion.registry import ExtractionResult

logger = logging.getLogger(__name__)


def flatten_json_dict(
    data: Any,
    prefix: str = "",
    sep: str = ".",
) -> List[Tuple[str, str]]:
    """Flatten a nested JSON dictionary or list into a list of (key_path, value_str) tuples.

    Args:
        data: Nested JSON object or array.
        prefix: Current path prefix.
        sep: Separator between key levels.

    Returns:
        List of (key, value) pairs.
    """
    items: List[Tuple[str, str]] = []

    if isinstance(data, dict):
        for k, v in data.items():
            new_key = f"{prefix}{sep}{k}" if prefix else k
            if isinstance(v, (dict, list)):
                items.extend(flatten_json_dict(v, new_key, sep=sep))
            else:
                items.append((new_key, str(v)))
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            new_key = f"{prefix}[{idx}]"
            if isinstance(item, (dict, list)):
                items.extend(flatten_json_dict(item, new_key, sep=sep))
            else:
                items.append((new_key, str(item)))
    else:
        items.append((prefix, str(data)))

    return items


class JSONExtractor:
    """Extracts text, key-value specifications, and metadata from JSON files."""

    def can_handle(self, file_path: Path) -> bool:
        """Check if file has a .json extension."""
        return file_path.suffix.lower() == ".json"

    async def extract(self, file_path: Path) -> ExtractionResult:
        """Extract content from a JSON file.

        Args:
            file_path: Path to .json file.

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
            content = file_path.read_text(encoding="utf-8")
            data = json.loads(content)
        except Exception as exc:
            logger.error("Failed to parse JSON %s: %s", file_path.name, exc)
            return ExtractionResult(
                text="",
                confidence=0.0,
                errors=[f"Failed to parse JSON: {str(exc)}"],
            )

        # 1. Detect metadata fields if present at top level
        metadata: Dict[str, Any] = {
            "filename": file_path.name,
            "title": file_path.stem.replace("_", " ").title(),
        }

        if isinstance(data, dict):
            for field in ("title", "revision", "document_id", "date", "author", "version", "system"):
                if field in data and isinstance(data[field], (str, int, float)):
                    metadata[field] = str(data[field])

            if "metadata" in data and isinstance(data["metadata"], dict):
                for k, v in data["metadata"].items():
                    if isinstance(v, (str, int, float)):
                        metadata[k] = str(v)

        # 2. Flatten JSON into key-values
        flat_pairs = flatten_json_dict(data)

        # 3. Create structured table from key-values
        tables: List[Dict[str, Any]] = []
        if flat_pairs:
            tables.append({
                "headers": ["Parameter / Field", "Value"],
                "rows": [[k, v] for k, v in flat_pairs],
            })

        # 4. Generate readable text representation
        lines = [f"# Document: {metadata.get('title', file_path.stem)}", ""]
        sections: List[Dict[str, Any]] = []

        if isinstance(data, dict):
            for section_name, val in data.items():
                sec_pairs = flatten_json_dict(val, prefix=section_name)
                sec_text = "\n".join(f"{k}: {v}" for k, v in sec_pairs)
                sections.append({
                    "heading": section_name.replace("_", " ").title(),
                    "content": sec_text,
                    "page": 1,
                })
                lines.append(f"## {section_name.title()}")
                lines.append(sec_text)
                lines.append("")
        else:
            full_flat = "\n".join(f"{k}: {v}" for k, v in flat_pairs)
            sections.append({
                "heading": "JSON Data",
                "content": full_flat,
                "page": 1,
            })
            lines.append(full_flat)

        full_text = "\n".join(lines).strip()

        return ExtractionResult(
            text=full_text,
            tables=tables,
            metadata=metadata,
            sections=sections,
            images=[],
            extraction_method="json",
            confidence=1.0,
            errors=[],
            page_count=1,
            raw_content=content,
        )
