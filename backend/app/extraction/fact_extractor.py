"""Engineering fact extraction pipeline for the Aegis Knowledge System.

Combines rule-based regex patterns, table structure parsing, JSON flattening,
and optional LLM-assisted extraction for unstructured prose.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.extraction.table_extractor import RawTableFact, TableExtractor
from app.extraction.text_chunker import TextChunk
from app.knowledge.models import ExtractionMethod
from app.normalization.unit_normalizer import normalize_unit, parse_value_unit

logger = logging.getLogger(__name__)

# Range pattern: e.g. -40°C to +85°C, 100 - 200 bar, 3000 +/- 50 PSI
_RANGE_REGEX = re.compile(
    r"([+-]?\d+(?:\.\d+)?)\s*(?:°C|°F|bar|PSI|kPa|MPa|GPM|L/min)?\s*(?:to|[-–—]|\+/-|±)\s*([+-]?\d+(?:\.\d+)?)\s*([a-zA-Z°℃℉Ωµ%\/\*\-\^0-9\.]+)?",
    re.IGNORECASE,
)

# Common engineering predicates in hydraulic systems
_PREDICATE_PATTERNS = [
    r"operating\s+pressure",
    r"maximum\s+operating\s+pressure",
    r"min(?:imum)?\s+operating\s+pressure",
    r"supply\s+pressure",
    r"return\s+pressure",
    r"proof\s+pressure",
    r"burst\s+pressure",
    r"cracking\s+pressure",
    r"relief\s+pressure",
    r"set\s+pressure",
    r"operating\s+temperature",
    r"temperature\s+range",
    r"ambient\s+temperature",
    r"fluid\s+temperature",
    r"max(?:imum)?\s+temperature",
    r"flow\s+rate",
    r"rated\s+flow",
    r"maximum\s+flow",
    r"nominal\s+flow",
    r"leakage\s+rate",
    r"fluid\s+type",
    r"hydraulic\s+fluid",
    r"recommended\s+fluid",
    r"viscosity",
    r"cleanliness\s+level",
    r"stroke\s+length",
    r"bore\s+diameter",
    r"rod\s+diameter",
    r"displacement",
    r"response\s+time",
    r"step\s+response",
    r"operating\s+voltage",
    r"supply\s+voltage",
    r"power\s+consumption",
    r"rated\s+current",
    r"frequency\s+response",
    r"reservoir\s+capacity",
    r"tank\s+capacity",
    r"filter\s+rating",
    r"filtration\s+rating",
    r"weight",
    r"dry\s+weight",
    r"mounting\s+type",
    r"port\s+size",
    r"seal\s+material",
    r"material",
]

_COMBINED_PREDICATES = "|".join(_PREDICATE_PATTERNS)

# Regex matching "Predicate: Value" or "Predicate = Value" or "Predicate - Value"
_SPEC_REGEX = re.compile(
    rf"(?P<predicate>{_COMBINED_PREDICATES})\s*[:=-]\s*(?P<value>[^\n;\r]+)",
    re.IGNORECASE,
)

# Component ID mention regex (e.g. PA-7100, SV-4200, ACT-PRI)
_COMPONENT_REF_REGEX = re.compile(
    r"\b([A-Z]{2,4}-?[0-9]{3,5}[A-Z]?|ACT-PRI|SRV-V1|HX-MAIN|FLT-PRI|PMP-1|ACC-1|RES-1|PRV-SYS)\b"
)


@dataclass
class ExtractedFactRecord:
    """Standardized extracted fact ready for entity linking and database persistence."""
    subject: str
    predicate: str
    value: str
    unit: Optional[str] = None
    numeric_value: Optional[float] = None
    tolerance_min: Optional[float] = None
    tolerance_max: Optional[float] = None
    extraction_method: ExtractionMethod = ExtractionMethod.PATTERN
    confidence: float = 0.90
    evidence_snippet: str = ""
    page_number: Optional[int] = None
    section_header: Optional[str] = None


def find_likely_subject(
    text: str,
    section_header: Optional[str] = None,
    default_subject: str = "Aegis System",
) -> str:
    """Identify the most likely component subject for a snippet of text.

    Args:
        text: Local text or sentence containing specification.
        section_header: Header of containing section.
        default_subject: Fallback subject.

    Returns:
        Identified component name or ID string.
    """
    # 1. Check section header for component ID
    if section_header:
        match = _COMPONENT_REF_REGEX.search(section_header)
        if match:
            return match.group(1).upper()

    # 2. Check local text for component ID
    match = _COMPONENT_REF_REGEX.search(text)
    if match:
        return match.group(1).upper()

    # 3. Check section header text itself
    if section_header and len(section_header.strip()) < 50:
        return section_header.strip()

    return default_subject


def parse_range_spec(raw_value: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """Parse tolerance or min-max range (e.g., '-40°C to +85°C' or '3000 ± 50 PSI').

    Args:
        raw_value: Range text string.

    Returns:
        Tuple of (min_val, max_val, normalized_unit).
    """
    match = _RANGE_REGEX.search(raw_value)
    if match:
        try:
            val1 = float(match.group(1))
            val2 = float(match.group(2))
            unit_str = match.group(3)
            norm_unit = normalize_unit(unit_str) if unit_str else None

            # Handle plus-minus
            if "±" in raw_value or "+/-" in raw_value:
                return round(val1 - val2, 4), round(val1 + val2, 4), norm_unit

            min_val = min(val1, val2)
            max_val = max(val1, val2)
            return round(min_val, 4), round(max_val, 4), norm_unit
        except ValueError:
            pass

    return None, None, None


class FactExtractor:
    """Multi-strategy fact extractor combining regex patterns, tables, JSON, and LLMs."""

    def __init__(self):
        """Initialize FactExtractor with table parser."""
        self.table_extractor = TableExtractor()

    def extract_from_patterns(
        self,
        chunk: TextChunk,
        default_subject: str = "Aegis System",
    ) -> List[ExtractedFactRecord]:
        """Extract facts using regex pattern matching on specifications.

        Args:
            chunk: TextChunk to analyze.
            default_subject: Default subject fallback.

        Returns:
            List of ExtractedFactRecord instances.
        """
        text = chunk.content
        facts: List[ExtractedFactRecord] = []

        for match in _SPEC_REGEX.finditer(text):
            pred_raw = match.group("predicate").strip().title()
            val_raw = match.group("value").strip().rstrip(".,;")

            if not val_raw or len(val_raw) > 120:
                continue

            # Determine subject
            # Look backwards from match position for nearest component reference
            prefix_window = text[max(0, match.start() - 200) : match.start()]
            subject = find_likely_subject(
                prefix_window,
                section_header=chunk.section_header,
                default_subject=default_subject,
            )

            # Check for range
            t_min, t_max, r_unit = parse_range_spec(val_raw)
            if t_min is not None and t_max is not None:
                numeric_val = (t_min + t_max) / 2.0
                unit = r_unit
                clean_val = val_raw
            else:
                numeric_val, unit, clean_val = parse_value_unit(val_raw)

            # Extract full sentence or line as snippet
            start_idx = max(0, text.rfind("\n", 0, match.start()))
            end_idx = text.find("\n", match.end())
            if end_idx == -1:
                end_idx = len(text)
            snippet = text[start_idx:end_idx].strip()

            facts.append(
                ExtractedFactRecord(
                    subject=subject,
                    predicate=pred_raw,
                    value=clean_val,
                    unit=unit,
                    numeric_value=numeric_val,
                    tolerance_min=t_min,
                    tolerance_max=t_max,
                    extraction_method=ExtractionMethod.PATTERN,
                    confidence=0.92,
                    evidence_snippet=snippet or f"{pred_raw}: {val_raw}",
                    page_number=chunk.page_number,
                    section_header=chunk.section_header,
                )
            )

        return facts

    def extract_from_tables(
        self,
        tables: List[Dict[str, Any]],
        default_subject: str = "Aegis System",
    ) -> List[ExtractedFactRecord]:
        """Extract facts from document tables.

        Args:
            tables: List of standardized table dictionaries.
            default_subject: Default subject.

        Returns:
            List of ExtractedFactRecord instances.
        """
        facts: List[ExtractedFactRecord] = []
        for idx, table in enumerate(tables):
            table_facts = self.table_extractor.extract_facts_from_table(
                table_dict=table,
                table_index=idx,
                context_subject=default_subject,
            )
            for tf in table_facts:
                facts.append(
                    ExtractedFactRecord(
                        subject=tf.subject,
                        predicate=tf.predicate.title(),
                        value=tf.value,
                        unit=tf.unit,
                        numeric_value=tf.numeric_value,
                        tolerance_min=tf.tolerance_min,
                        tolerance_max=tf.tolerance_max,
                        extraction_method=ExtractionMethod.TABLE,
                        confidence=0.95,
                        evidence_snippet=tf.raw_snippet,
                        page_number=None,
                        section_header=f"Table {idx + 1}",
                    )
                )
        return facts

    def extract_from_json_dict(
        self,
        data: Any,
        parent_key: str = "",
        subject: str = "Aegis System",
    ) -> List[ExtractedFactRecord]:
        """Recursively extract key-value facts from JSON structures.

        Args:
            data: Parsed JSON structure.
            parent_key: Accumulated key path.
            subject: Subject component.

        Returns:
            List of ExtractedFactRecord instances.
        """
        facts: List[ExtractedFactRecord] = []

        if isinstance(data, dict):
            # Check if this level defines a component
            curr_subject = subject
            if "component_id" in data:
                curr_subject = str(data["component_id"]).strip()
            elif "component" in data and isinstance(data["component"], str):
                curr_subject = str(data["component"]).strip()
            elif "id" in data and isinstance(data["id"], str) and "-" in data["id"]:
                curr_subject = str(data["id"]).strip()

            for k, v in data.items():
                if k in ("component_id", "component", "id", "metadata"):
                    continue
                nested_key = f"{parent_key}.{k}" if parent_key else k
                if isinstance(v, (dict, list)):
                    facts.extend(self.extract_from_json_dict(v, nested_key, curr_subject))
                else:
                    v_str = str(v).strip()
                    num_val, unit, formatted_val = parse_value_unit(v_str)
                    clean_pred = nested_key.replace("_", " ").title()
                    facts.append(
                        ExtractedFactRecord(
                            subject=curr_subject,
                            predicate=clean_pred,
                            value=formatted_val if num_val is not None else v_str,
                            unit=unit,
                            numeric_value=num_val,
                            extraction_method=ExtractionMethod.RULE,
                            confidence=0.98,
                            evidence_snippet=f'"{nested_key}": "{v_str}"',
                            page_number=1,
                            section_header="JSON Specification",
                        )
                    )
        elif isinstance(data, list):
            for idx, item in enumerate(data):
                facts.extend(
                    self.extract_from_json_dict(item, f"{parent_key}[{idx}]", subject)
                )

        return facts

    async def extract_from_llm(
        self,
        chunk: TextChunk,
        subject: str = "Aegis System",
    ) -> List[ExtractedFactRecord]:
        """Optional LLM extraction for unstructured text using OpenAI API when configured.

        Args:
            chunk: Text chunk.
            subject: Context subject.

        Returns:
            List of ExtractedFactRecord instances extracted by LLM.
        """
        if not settings.OPENAI_API_KEY:
            logger.debug("OpenAI API key not configured. Skipping LLM fact extraction.")
            return []

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
            )

            prompt = (
                "You are an expert hydraulic systems engineering fact extractor. "
                "Extract all technical specifications, component parameters, and engineering limits "
                "from the text below. For each fact, return a JSON object with: "
                "subject (component ID or name), predicate (parameter name), value (clean value string), "
                "unit (engineering unit or null), numeric_value (float or null), evidence_snippet (exact text snippet).\n\n"
                f"Context subject: {subject}\n"
                f"Text:\n{chunk.content}\n\n"
                "Return a JSON array of objects. Do not include markdown code block formatting."
            )

            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You output only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )

            raw_content = response.choices[0].message.content or ""
            # Strip markdown code blocks if returned
            clean_json = raw_content.strip()
            if clean_json.startswith("```"):
                clean_json = re.sub(r"^```[a-zA-Z]*\n?", "", clean_json)
                clean_json = re.sub(r"\n?```$", "", clean_json)

            data = json.loads(clean_json)
            facts: List[ExtractedFactRecord] = []
            if isinstance(data, list):
                for item in data:
                    s = item.get("subject") or subject
                    p = item.get("predicate", "").title()
                    v = str(item.get("value", ""))
                    u = normalize_unit(item.get("unit"))
                    nv = item.get("numeric_value")
                    snip = item.get("evidence_snippet") or chunk.content[:150]

                    if p and v:
                        facts.append(
                            ExtractedFactRecord(
                                subject=s,
                                predicate=p,
                                value=v,
                                unit=u,
                                numeric_value=float(nv) if nv is not None else None,
                                extraction_method=ExtractionMethod.LLM,
                                confidence=0.85,
                                evidence_snippet=snip,
                                page_number=chunk.page_number,
                                section_header=chunk.section_header,
                            )
                        )
            return facts
        except Exception as exc:
            logger.warning("LLM fact extraction encountered an error: %s", exc)
            return []
