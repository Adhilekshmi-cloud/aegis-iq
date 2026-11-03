"""Hybrid document and knowledge retriever combining semantic FAISS search and SQLite keyword search using Reciprocal Rank Fusion (RRF)."""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.models import Conflict, Document, DocumentChunk, Entity, Fact
from app.retrieval.embeddings import EmbeddingService, get_embedding_service
from app.retrieval.faiss_index import FAISSIndexService, VectorSearchResult
from app.retrieval.keyword_search import KeywordSearchResult, KeywordSearcher

logger = logging.getLogger(__name__)

RRF_K = 60  # Standard Reciprocal Rank Fusion constant


@dataclass
class RetrievedChunk:
    """Document chunk returned by hybrid search with fusion score."""
    chunk_id: str
    content: str
    section_header: Optional[str]
    page_number: Optional[int]
    document_title: Optional[str]
    document_filename: Optional[str]
    rrf_score: float
    semantic_rank: Optional[int] = None
    keyword_rank: Optional[int] = None


@dataclass
class HybridRetrievalResult:
    """Unified retrieval payload containing fused chunks, matching facts, and conflicts."""
    query: str
    chunks: List[RetrievedChunk] = field(default_factory=list)
    facts: List[Dict[str, Any]] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)


class HybridRetriever:
    """Coordinates hybrid retrieval over FAISS vectors and SQLite relational knowledge."""

    def __init__(
        self,
        faiss_service: Optional[FAISSIndexService] = None,
        embedding_service: Optional[EmbeddingService] = None,
        keyword_searcher: Optional[KeywordSearcher] = None,
    ):
        """Initialize retriever.

        Args:
            faiss_service: FAISS vector index instance.
            embedding_service: Embedding generation service.
            keyword_searcher: Lexical keyword searcher.
        """
        self.faiss_service = faiss_service or FAISSIndexService()
        self.embedding_service = embedding_service or get_embedding_service()
        self.keyword_searcher = keyword_searcher or KeywordSearcher()

    async def retrieve(
        self,
        session: AsyncSession,
        query: str,
        top_k: int = 5,
        target_entity_ids: Optional[List[str]] = None,
    ) -> HybridRetrievalResult:
        """Execute hybrid search combining dense semantic ranking and lexical BM25 ranking.

        Args:
            session: Active database AsyncSession.
            query: User prompt or question string.
            top_k: Number of unified chunks to return.
            target_entity_ids: Optional list of entity IDs to filter or prioritize facts.

        Returns:
            HybridRetrievalResult containing fused chunks, linked facts, and any detected conflicts.
        """
        logger.info("Executing hybrid retrieval for query: '%s'", query)

        # 1. Semantic Search via FAISS
        query_vector = self.embedding_service.encode_text(query)
        semantic_results: List[VectorSearchResult] = self.faiss_service.search(
            query_vector, top_k=top_k * 2
        )

        # 2. Keyword Search via SQLite
        keyword_results: List[KeywordSearchResult] = (
            await self.keyword_searcher.search_chunks(session, query, limit=top_k * 2)
        )

        # 3. Reciprocal Rank Fusion (RRF)
        # RRF Score = sum(1 / (RRF_K + rank))
        rrf_scores: Dict[str, float] = {}
        semantic_ranks: Dict[str, int] = {}
        keyword_ranks: Dict[str, int] = {}

        for rank, res in enumerate(semantic_results, start=1):
            c_id = res.chunk_id
            semantic_ranks[c_id] = rank
            rrf_scores[c_id] = rrf_scores.get(c_id, 0.0) + (1.0 / (RRF_K + rank))

        for rank, res in enumerate(keyword_results, start=1):
            c_id = res.id
            keyword_ranks[c_id] = rank
            rrf_scores[c_id] = rrf_scores.get(c_id, 0.0) + (1.0 / (RRF_K + rank))

        # Sort chunk IDs by descending RRF score
        sorted_chunk_ids = sorted(
            rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True
        )[:top_k]

        # 4. Fetch full DocumentChunk records from SQLite for top chunks
        retrieved_chunks: List[RetrievedChunk] = []
        chunk_doc_ids: Set[str] = set()

        if sorted_chunk_ids:
            chunk_stmt = select(DocumentChunk).where(DocumentChunk.chunk_id.in_(sorted_chunk_ids))
            c_res = await session.execute(chunk_stmt)
            chunk_map = {c.chunk_id: c for c in c_res.scalars().all()}

            # Fetch associated documents
            for cid in sorted_chunk_ids:
                chk = chunk_map.get(cid)
                if chk:
                    chunk_doc_ids.add(chk.document_id)

            doc_map: Dict[str, Document] = {}
            if chunk_doc_ids:
                doc_stmt = select(Document).where(Document.document_id.in_(list(chunk_doc_ids)))
                d_res = await session.execute(doc_stmt)
                doc_map = {d.document_id: d for d in d_res.scalars().all()}

            for cid in sorted_chunk_ids:
                chk = chunk_map.get(cid)
                if chk:
                    parent_doc = doc_map.get(chk.document_id)
                    retrieved_chunks.append(
                        RetrievedChunk(
                            chunk_id=chk.chunk_id,
                            content=chk.content,
                            section_header=chk.section_header,
                            page_number=chk.page_number,
                            document_title=parent_doc.doc_title if parent_doc else None,
                            document_filename=parent_doc.filename if parent_doc else None,
                            rrf_score=round(rrf_scores[cid], 5),
                            semantic_rank=semantic_ranks.get(cid),
                            keyword_rank=keyword_ranks.get(cid),
                        )
                    )

        # 5. Fetch associated Facts and Conflicts
        # Look up facts either by target_entity_ids or lexical match
        matched_facts_data: List[Dict[str, Any]] = []
        matched_conflicts_data: List[Dict[str, Any]] = []
        matched_entities_data: List[Dict[str, Any]] = []

        fact_kw_res = await self.keyword_searcher.search_facts(session, query, limit=10)
        found_fact_ids = [res.id for res in fact_kw_res]

        fact_filters = []
        if target_entity_ids:
            fact_filters.append(Fact.entity_id.in_(target_entity_ids))
        if found_fact_ids:
            fact_filters.append(Fact.fact_id.in_(found_fact_ids))

        if fact_filters:
            from sqlalchemy import or_
            fact_stmt = select(Fact).where(or_(*fact_filters)).limit(20)
            f_exec = await session.execute(fact_stmt)
            facts_list = f_exec.scalars().all()

            for f in facts_list:
                matched_facts_data.append({
                    "fact_id": f.fact_id,
                    "entity_id": f.entity_id,
                    "predicate": f.predicate,
                    "value": f.value,
                    "unit": f.unit,
                    "numeric_value": f.numeric_value,
                    "status": f.verification_status.value,
                    "confidence": f.confidence_score,
                })
                # Check for attached conflicts
                for conf in f.conflicts:
                    matched_conflicts_data.append({
                        "conflict_id": conf.conflict_id,
                        "type": conf.conflict_type.value,
                        "predicate": conf.predicate,
                        "description": conf.description,
                        "status": conf.status.value,
                    })

        # Fetch entities
        ent_kw_res = await self.keyword_searcher.search_entities(session, query, limit=5)
        for e in ent_kw_res:
            matched_entities_data.append({
                "entity_id": e.id,
                "canonical_name": e.title,
                "score": e.score,
            })

        return HybridRetrievalResult(
            query=query,
            chunks=retrieved_chunks,
            facts=matched_facts_data,
            conflicts=matched_conflicts_data,
            entities=matched_entities_data,
        )
