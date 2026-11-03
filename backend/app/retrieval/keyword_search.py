"""SQLite-based keyword and term search for entities, facts, and document chunks."""

import logging
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.models import DocumentChunk, Entity, EntityAlias, Fact

logger = logging.getLogger(__name__)


@dataclass
class KeywordSearchResult:
    """Standardized result of a keyword search query."""
    item_type: str  # "chunk", "fact", "entity"
    id: str
    score: float
    title: str
    snippet: str
    metadata: Dict[str, Any] = field(default_factory=dict)


def compute_bm25_score(
    query_terms: List[str],
    text: str,
    avg_len: float = 100.0,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    """Compute lightweight BM25-like lexical relevance score.

    Args:
        query_terms: List of query keywords.
        text: Document or snippet string.
        avg_len: Average field length heuristic.
        k1: BM25 saturation parameter.
        b: BM25 document length normalization parameter.

    Returns:
        Lexical score >= 0.0.
    """
    if not query_terms or not text:
        return 0.0

    text_lower = text.lower()
    doc_words = text_lower.split()
    doc_len = len(doc_words)

    score = 0.0
    for term in query_terms:
        term_clean = term.lower()
        # Count occurrences
        tf = text_lower.count(term_clean)
        if tf > 0:
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * (doc_len / avg_len))
            score += (numerator / denominator)

            # Bonus for exact word boundary match
            if re.search(rf"\b{re.escape(term_clean)}\b", text_lower):
                score += 0.5

    return round(score, 4)


class KeywordSearcher:
    """Performs lexical queries against SQLite database tables for entities, facts, and chunks."""

    async def search_chunks(
        self,
        session: AsyncSession,
        query: str,
        limit: int = 10,
    ) -> List[KeywordSearchResult]:
        """Search DocumentChunks for occurrences of query keywords.

        Args:
            session: Active database AsyncSession.
            query: User search text or question.
            limit: Maximum results to return.

        Returns:
            List of KeywordSearchResult for matching chunks.
        """
        terms = [t.strip() for t in query.split() if len(t.strip()) > 1]
        if not terms:
            return []

        # Filter chunks containing at least one term
        filters = [DocumentChunk.content.ilike(f"%{term}%") for term in terms]
        stmt = select(DocumentChunk).where(or_(*filters)).limit(limit * 3)
        res = await session.execute(stmt)
        chunks = res.scalars().all()

        results: List[KeywordSearchResult] = []
        for chk in chunks:
            score = compute_bm25_score(terms, chk.content)
            if score > 0:
                # Highlight or create snippet
                snippet = chk.content[:250] + ("..." if len(chk.content) > 250 else "")
                results.append(
                    KeywordSearchResult(
                        item_type="chunk",
                        id=chk.chunk_id,
                        score=score,
                        title=chk.section_header or f"Chunk #{chk.chunk_index}",
                        snippet=snippet,
                        metadata={
                            "document_id": chk.document_id,
                            "page_number": chk.page_number,
                            "token_count": chk.token_count,
                        },
                    )
                )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    async def search_facts(
        self,
        session: AsyncSession,
        query: str,
        limit: int = 10,
    ) -> List[KeywordSearchResult]:
        """Search Facts by matching predicate, value, or unit.

        Args:
            session: Active database AsyncSession.
            query: Query string.
            limit: Max results.

        Returns:
            List of KeywordSearchResult for matching facts.
        """
        terms = [t.strip() for t in query.split() if len(t.strip()) > 1]
        if not terms:
            return []

        filters = []
        for term in terms:
            filters.append(Fact.predicate.ilike(f"%{term}%"))
            filters.append(Fact.value.ilike(f"%{term}%"))

        stmt = select(Fact).where(or_(*filters)).limit(limit * 3)
        res = await session.execute(stmt)
        facts = res.scalars().all()

        results: List[KeywordSearchResult] = []
        for fact in facts:
            combined = f"{fact.predicate} {fact.value} {fact.unit or ''}"
            score = compute_bm25_score(terms, combined)
            if score > 0:
                results.append(
                    KeywordSearchResult(
                        item_type="fact",
                        id=fact.fact_id,
                        score=score + 0.5,  # Boost structured facts slightly
                        title=fact.predicate,
                        snippet=f"{fact.predicate}: {fact.value} {fact.unit or ''}".strip(),
                        metadata={
                            "entity_id": fact.entity_id,
                            "value": fact.value,
                            "unit": fact.unit,
                            "numeric_value": fact.numeric_value,
                            "verification_status": fact.verification_status.value,
                        },
                    )
                )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    async def search_entities(
        self,
        session: AsyncSession,
        query: str,
        limit: int = 5,
    ) -> List[KeywordSearchResult]:
        """Search Entities and Aliases by canonical name or alias.

        Args:
            session: Active database AsyncSession.
            query: Query string.
            limit: Max results.

        Returns:
            List of KeywordSearchResult for matching entities.
        """
        terms = [t.strip() for t in query.split() if len(t.strip()) > 1]
        if not terms:
            return []

        filters = []
        for term in terms:
            filters.append(Entity.canonical_name.ilike(f"%{term}%"))

        stmt = select(Entity).where(or_(*filters)).limit(limit)
        res = await session.execute(stmt)
        entities = res.scalars().all()

        results: List[KeywordSearchResult] = []
        for ent in entities:
            score = compute_bm25_score(terms, ent.canonical_name)
            results.append(
                KeywordSearchResult(
                    item_type="entity",
                    id=ent.entity_id,
                    score=score + 1.0,  # Exact entity matches receive high priority
                    title=ent.canonical_name,
                    snippet=ent.description or f"Entity {ent.canonical_name} ({ent.entity_type.value})",
                    metadata={
                        "canonical_name": ent.canonical_name,
                        "entity_type": ent.entity_type.value,
                    },
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]
