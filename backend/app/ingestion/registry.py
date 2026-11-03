"""Extractor registry and protocol definitions for document ingestion."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Protocol

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Standardized output produced by format-specific document extractors."""
    text: str
    tables: List[dict] = field(default_factory=list)  # list of {headers: [...], rows: [[...], ...]}
    metadata: dict = field(default_factory=dict)  # title, author, date, revision, etc.
    sections: List[dict] = field(default_factory=list)  # {heading: str, content: str, page: int}
    images: List[dict] = field(default_factory=list)  # {description: str, page: int}
    extraction_method: str = "native"
    confidence: float = 1.0
    errors: List[str] = field(default_factory=list)
    page_count: int = 0
    raw_content: str = ""  # Original unprocessed content


class ExtractorProtocol(Protocol):
    """Protocol defining the interface for document format extractors."""

    def can_handle(self, file_path: Path) -> bool:
        """Check whether this extractor supports the given file format or extension."""
        ...

    async def extract(self, file_path: Path) -> ExtractionResult:
        """Extract structured text, tables, and metadata from the document."""
        ...


class ExtractorRegistry:
    """Registry managing available document extractors."""

    def __init__(self):
        """Initialize an empty extractor registry."""
        self._extractors: List[ExtractorProtocol] = []

    def register(self, extractor: ExtractorProtocol) -> None:
        """Register a format extractor instance."""
        self._extractors.append(extractor)
        logger.debug("Registered extractor: %s", extractor.__class__.__name__)

    def get_extractor(self, file_path: Path) -> Optional[ExtractorProtocol]:
        """Find the first registered extractor capable of processing the file path.

        Args:
            file_path: Path to target document file.

        Returns:
            Matching ExtractorProtocol implementation, or None.
        """
        for extractor in self._extractors:
            try:
                if extractor.can_handle(file_path):
                    return extractor
            except Exception as exc:
                logger.warning(
                    "Extractor %s failed can_handle check for %s: %s",
                    extractor.__class__.__name__,
                    file_path.name,
                    exc,
                )
        return None


# Global default registry
default_extractor_registry = ExtractorRegistry()
