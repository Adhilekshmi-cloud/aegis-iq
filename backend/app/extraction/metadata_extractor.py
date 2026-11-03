"""Metadata extraction from document text, headers, and paths for Aegis Knowledge System.

Extracts revision numbers, document IDs, publication dates, and ECN references,
and assigns trust level ratings in accordance with the Aegis system hierarchy.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.knowledge.models import DocumentType, TrustLevel

logger = logging.getLogger(__name__)

# Revision patterns: Rev A, Rev. B, Revision C, Rev 2.1, Revision: B
_REVISION_REGEX = re.compile(
    r"(?:(?:rev(?:ision)?\.?|version|ver\.?)\s*[:#-]?\s*([A-Z0-9]+(?:\.[0-9]+)?))",
    re.IGNORECASE,
)

# Document ID patterns: XX-XX-1234, DOC-001, MAN-7100, ECN-2024-001, AEGIS-SPEC-7100
_DOC_ID_REGEX = re.compile(
    r"\b([A-Z]{2,6}(?:-[A-Z0-9]+){1,3})\b"
)

# ECN reference patterns: ECN-2024-001, ECN #402, Engineering Change Notice 102
_ECN_REGEX = re.compile(
    r"(?:ECN\s*[-#:]?\s*([A-Za-z0-9\-]+)|engineering\s+change\s+notice\s*(?:#|no\.?|num)?\s*([A-Za-z0-9\-]+))",
    re.IGNORECASE,
)

# Date patterns (ISO: 2024-05-18, US: 05/18/2024 or 5-18-2024, Words: May 18, 2024)
_DATE_PATTERNS = [
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),  # YYYY-MM-DD
    re.compile(r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\b"),  # MM/DD/YYYY or DD/MM/YYYY
    re.compile(
        r"\b((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4})\b",
        re.IGNORECASE,
    ),
]


@dataclass
class ExtractedMetadata:
    """Document metadata extracted from raw text and filename."""
    title: Optional[str] = None
    document_id: Optional[str] = None
    revision: Optional[str] = None
    date: Optional[str] = None
    trust_level: TrustLevel = TrustLevel.MEDIUM
    ecn_references: List[str] = field(default_factory=list)
    author: Optional[str] = None
    source_system: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


def extract_revision(text: str) -> Optional[str]:
    """Extract revision identifier (e.g. 'Rev A', 'Revision B', 'Rev 1.2').

    Args:
        text: Text to scan.

    Returns:
        Revision code (e.g. 'A', 'B', '1.2') or None.
    """
    if not text:
        return None
    match = _REVISION_REGEX.search(text)
    if match:
        rev = match.group(1).strip().upper()
        return rev
    return None


def extract_document_id(text: str, filename: Optional[str] = None) -> Optional[str]:
    """Extract document identification code.

    Args:
        text: Text snippet or header.
        filename: Optional filename for fallback.

    Returns:
        Document ID code or None.
    """
    # Check text first
    if text:
        # Check first 2000 chars where header doc IDs normally reside
        header_sample = text[:2000]
        matches = _DOC_ID_REGEX.findall(header_sample)
        for m in matches:
            m_upper = m.upper()
            if any(p in m_upper for p in ("DOC", "SPEC", "MAN", "ECN", "SOP", "QA", "TB", "BULLETIN")):
                return m_upper
        if matches:
            return matches[0].upper()

    # Fallback to filename
    if filename:
        name_stem = Path(filename).stem
        match = _DOC_ID_REGEX.search(name_stem)
        if match:
            return match.group(1).upper()

    return None


def extract_dates(text: str) -> List[str]:
    """Find all date strings in the given text.

    Args:
        text: Document content.

    Returns:
        List of matched date strings.
    """
    if not text:
        return []
    dates: List[str] = []
    sample = text[:4000]  # Look near front of doc
    for pat in _DATE_PATTERNS:
        for m in pat.finditer(sample):
            dates.append(m.group(1).strip())
    return dates


def extract_ecn_references(text: str) -> List[str]:
    """Extract all Engineering Change Notice (ECN) reference codes.

    Args:
        text: Document content.

    Returns:
        List of ECN reference IDs.
    """
    if not text:
        return []
    ecns = set()
    for match in _ECN_REGEX.finditer(text):
        ecn_val = match.group(1) or match.group(2)
        if ecn_val:
            cleaned = ecn_val.strip().upper()
            if not cleaned.startswith("ECN"):
                cleaned = f"ECN-{cleaned}"
            ecns.add(cleaned)
    return sorted(list(ecns))


def determine_trust_level(
    filename: str,
    doc_type: DocumentType,
    text: str = "",
    ecn_refs: Optional[List[str]] = None,
) -> TrustLevel:
    """Determine trust level according to the Aegis system hierarchy.

    Hierarchy:
    - HIGH: Official manuals, ECNs, technical bulletins, OEM engineering specs
    - MEDIUM: Maintenance guides, QA reports, training materials, operating procedures
    - LOW: Field notes, informal communications, scratch logs

    Args:
        filename: Document file name.
        doc_type: DocumentType enum.
        text: Extracted text preview.
        ecn_refs: Extracted ECN references.

    Returns:
        Assigned TrustLevel enum.
    """
    fn_lower = filename.lower()
    text_sample = text[:2000].lower() if text else ""

    # HIGH trust indicators
    high_keywords = [
        "ecn",
        "manual",
        "specification",
        "spec",
        "bulletin",
        "oem",
        "datasheet",
        "technical_bulletin",
        "series-7",
    ]
    if any(k in fn_lower for k in high_keywords) or (ecn_refs and len(ecn_refs) > 0):
        return TrustLevel.HIGH

    if any(k in text_sample for k in ["engineering change notice", "technical specification", "oem manual"]):
        return TrustLevel.HIGH

    # LOW trust indicators
    low_keywords = ["notes", "field", "informal", "memo", "scratch", "email", "draft"]
    if any(k in fn_lower for k in low_keywords) or any(k in text_sample for k in ["field notes", "draft only"]):
        return TrustLevel.LOW

    # Default to MEDIUM for maintenance procedures, QA records, spreadsheets, slides
    return TrustLevel.MEDIUM


class MetadataExtractor:
    """Extractor for synthesizing document metadata and trust ratings."""

    def extract_metadata(
        self,
        file_path: Path,
        doc_type: DocumentType,
        text: str,
        extractor_meta: Optional[Dict[str, Any]] = None,
    ) -> ExtractedMetadata:
        """Extract all metadata from document text and environment.

        Args:
            file_path: Path to the document.
            doc_type: Recognized DocumentType.
            text: Extracted plain text content.
            extractor_meta: Pre-extracted format-specific metadata (PDF info, docx props, etc.).

        Returns:
            ExtractedMetadata instance.
        """
        raw_meta = extractor_meta or {}
        filename = file_path.name

        # Revision
        rev = raw_meta.get("revision") or extract_revision(text[:3000])

        # Document ID
        doc_id = raw_meta.get("document_id") or extract_document_id(text[:3000], filename=filename)

        # Dates
        dates = extract_dates(text)
        primary_date = raw_meta.get("date") or (dates[0] if dates else None)

        # ECNs
        ecns = extract_ecn_references(text)

        # Title
        title = raw_meta.get("title")
        if not title:
            # Fallback to first non-empty header or filename stem
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if lines and len(lines[0]) < 80:
                title = lines[0]
            else:
                title = file_path.stem.replace("_", " ").title()

        # Trust level
        trust = determine_trust_level(filename, doc_type, text, ecn_refs=ecns)

        author = raw_meta.get("author")

        return ExtractedMetadata(
            title=title,
            document_id=doc_id,
            revision=rev,
            date=primary_date,
            trust_level=trust,
            ecn_references=ecns,
            author=author,
            source_system="Aegis Series-7 Hydraulic Control System",
            extra=raw_meta,
        )
