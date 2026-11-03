"""Section-aware text chunking for technical documents in Aegis Knowledge System.

Splits document text into manageable token/word chunks respecting structural
boundaries (headings, sections, paragraphs) while providing configurable overlap.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default configurations
DEFAULT_MAX_CHUNK_TOKENS = 512
DEFAULT_OVERLAP_TOKENS = 64

# Regex for section headers (Markdown, numbered sections, uppercase headers)
_HEADING_REGEX = re.compile(
    r"^(?:#{1,6}\s+.+|[0-9]+(?:\.[0-9]+)*\s+[A-Z].+|[A-Z0-9\s\-_]{3,40}:|[A-Z\s]{4,40}$)",
    re.MULTILINE,
)


@dataclass
class TextChunk:
    """A single bounded segment of document text with associated metadata."""
    content: str
    chunk_index: int
    section_header: Optional[str] = None
    page_number: Optional[int] = None
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


def estimate_token_count(text: str) -> int:
    """Approximate the token count of a string (approx. 1 token per 0.75 words / 4 chars).

    Args:
        text: Input string.

    Returns:
        Estimated integer token count.
    """
    if not text:
        return 0
    words = text.split()
    return max(1, int(len(words) * 1.25))


class TextChunker:
    """Configurable text chunker preserving section headings and supporting context overlap."""

    def __init__(
        self,
        max_chunk_tokens: int = DEFAULT_MAX_CHUNK_TOKENS,
        overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
    ):
        """Initialize chunker.

        Args:
            max_chunk_tokens: Maximum target token count per chunk.
            overlap_tokens: Token count overlap carried from preceding chunk.
        """
        self.max_chunk_tokens = max_chunk_tokens
        self.overlap_tokens = min(overlap_tokens, max_chunk_tokens // 2)

    def chunk_section(
        self,
        heading: Optional[str],
        content: str,
        page_number: Optional[int] = None,
        base_index: int = 0,
        extra_meta: Optional[Dict[str, Any]] = None,
    ) -> List[TextChunk]:
        """Split a single titled section's content into overlapping chunks.

        Args:
            heading: Section heading title.
            content: Raw text content of the section.
            page_number: Page number the section appears on.
            base_index: Starting chunk index.
            extra_meta: Additional metadata dictionary.

        Returns:
            List of TextChunk instances.
        """
        if not content or not content.strip():
            return []

        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [content.strip()]

        chunks: List[TextChunk] = []
        current_words: List[str] = []
        current_header = heading

        # If heading exists, we prepend it conceptually to context
        prefix_words = heading.split() if heading else []

        for p in paragraphs:
            p_words = p.split()
            # If paragraph itself is longer than max allowed tokens, split by sentence/words
            if estimate_token_count(" ".join(p_words)) > self.max_chunk_tokens:
                # Flush current words first
                if current_words:
                    chunk_text = " ".join(current_words)
                    chunks.append(
                        TextChunk(
                            content=chunk_text,
                            chunk_index=base_index + len(chunks),
                            section_header=current_header,
                            page_number=page_number,
                            token_count=estimate_token_count(chunk_text),
                            metadata=extra_meta.copy() if extra_meta else {},
                        )
                    )
                    overlap_words = current_words[-self.overlap_tokens :] if self.overlap_tokens > 0 else []
                    current_words = list(overlap_words)

                # Split long paragraph in word steps
                step = self.max_chunk_tokens - self.overlap_tokens
                for i in range(0, len(p_words), step):
                    sub_words = p_words[i : i + self.max_chunk_tokens]
                    chunk_text = " ".join(sub_words)
                    chunks.append(
                        TextChunk(
                            content=chunk_text,
                            chunk_index=base_index + len(chunks),
                            section_header=current_header,
                            page_number=page_number,
                            token_count=estimate_token_count(chunk_text),
                            metadata=extra_meta.copy() if extra_meta else {},
                        )
                    )
                current_words = []
                continue

            test_text = " ".join(current_words + p_words)
            if estimate_token_count(test_text) <= self.max_chunk_tokens:
                current_words.extend(p_words)
            else:
                if current_words:
                    chunk_text = " ".join(current_words)
                    chunks.append(
                        TextChunk(
                            content=chunk_text,
                            chunk_index=base_index + len(chunks),
                            section_header=current_header,
                            page_number=page_number,
                            token_count=estimate_token_count(chunk_text),
                            metadata=extra_meta.copy() if extra_meta else {},
                        )
                    )
                    # Carry forward overlap
                    overlap_words = current_words[-self.overlap_tokens :] if self.overlap_tokens > 0 else []
                    current_words = list(overlap_words) + p_words
                else:
                    current_words = list(p_words)

        if current_words:
            chunk_text = " ".join(current_words)
            chunks.append(
                TextChunk(
                    content=chunk_text,
                    chunk_index=base_index + len(chunks),
                    section_header=current_header,
                    page_number=page_number,
                    token_count=estimate_token_count(chunk_text),
                    metadata=extra_meta.copy() if extra_meta else {},
                )
            )

        return chunks

    def chunk_document(
        self,
        full_text: str,
        sections: Optional[List[Dict[str, Any]]] = None,
        page_count: int = 0,
        extra_meta: Optional[Dict[str, Any]] = None,
    ) -> List[TextChunk]:
        """Chunk an entire document text into section-aware TextChunks.

        Args:
            full_text: Complete document text.
            sections: Optional extracted sections [{heading: str, content: str, page: int}].
            page_count: Number of document pages.
            extra_meta: Metadata to attach to each chunk.

        Returns:
            List of TextChunk instances.
        """
        all_chunks: List[TextChunk] = []

        if sections:
            # Chunk along pre-extracted section boundaries
            for sec in sections:
                heading = sec.get("heading")
                content = sec.get("content", "")
                page = sec.get("page", 1)
                sec_chunks = self.chunk_section(
                    heading=heading,
                    content=content,
                    page_number=page,
                    base_index=len(all_chunks),
                    extra_meta=extra_meta,
                )
                all_chunks.extend(sec_chunks)
        else:
            # Detect section headings dynamically from full_text
            lines = full_text.split("\n")
            current_heading = "General"
            current_section_lines: List[str] = []

            for line in lines:
                stripped = line.strip()
                if _HEADING_REGEX.match(stripped):
                    # Flush previous section
                    sec_text = "\n".join(current_section_lines).strip()
                    if sec_text:
                        sec_chunks = self.chunk_section(
                            heading=current_heading,
                            content=sec_text,
                            page_number=1,
                            base_index=len(all_chunks),
                            extra_meta=extra_meta,
                        )
                        all_chunks.extend(sec_chunks)
                    current_heading = stripped
                    current_section_lines = []
                else:
                    current_section_lines.append(line)

            # Flush final section
            final_text = "\n".join(current_section_lines).strip()
            if final_text:
                sec_chunks = self.chunk_section(
                    heading=current_heading,
                    content=final_text,
                    page_number=1,
                    base_index=len(all_chunks),
                    extra_meta=extra_meta,
                )
                all_chunks.extend(sec_chunks)

        logger.debug("Document chunked into %d chunks", len(all_chunks))
        return all_chunks
