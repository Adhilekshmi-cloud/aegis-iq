"""Evidence assembler - gathers, ranks, and groups evidence for answering questions."""

import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.knowledge.models import (
    Entity, EntityAlias, Fact, Evidence, Conflict, Document,
    VerificationStatus, TrustLevel, conflict_facts,
)
from app.reasoning.query_analyzer import QueryAnalysis

logger = logging.getLogger(__name__)


@dataclass
class EvidenceItem:
    """A single piece of evidence supporting or contradicting a claim."""
    fact_id: str
    subject: str
    predicate: str
    value: str
    unit: Optional[str]
    document_name: str
    document_id: str
    page_number: Optional[int]
    section: Optional[str]
    source_text: Optional[str]
    trust_level: str
    confidence: float
    extraction_method: str
    revision_scope: Optional[str]
    verification_status: str
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None


@dataclass
class ConflictGroup:
    """A group of conflicting evidence items."""
    conflict_id: str
    conflict_type: str
    resolution_status: str
    explanation: Optional[str]
    items: list[EvidenceItem] = field(default_factory=list)


@dataclass
class AssembledEvidence:
    """All evidence gathered for a query, organized by agreement and conflict."""
    query_analysis: QueryAnalysis
    supporting_evidence: list[EvidenceItem] = field(default_factory=list)
    conflicts: list[ConflictGroup] = field(default_factory=list)
    all_evidence: list[EvidenceItem] = field(default_factory=list)
    matched_entities: list[dict] = field(default_factory=list)
    total_sources: int = 0


class EvidenceAssembler:
    """Gathers and organizes evidence from the knowledge store for a query."""

    async def assemble(
        self, db: AsyncSession, analysis: QueryAnalysis
    ) -> AssembledEvidence:
        """Assemble all relevant evidence for a query analysis.
        
        Args:
            db: Database session.
            analysis: The analyzed query.
            
        Returns:
            AssembledEvidence with organized supporting and conflicting evidence.
        """
        logger.info(f"Assembling evidence for: {analysis.original_question}")
        
        result = AssembledEvidence(query_analysis=analysis)
        
        # Step 1: Find matching entities
        entity_ids = await self._find_matching_entities(db, analysis)
        
        # Step 2: Find relevant facts
        facts = await self._find_relevant_facts(db, entity_ids, analysis)
        
        # Step 3: Load evidence for each fact
        for fact in facts:
            evidence_items = await self._load_evidence_for_fact(db, fact)
            result.all_evidence.extend(evidence_items)
        
        # Step 4: Find conflicts
        result.conflicts = await self._find_conflicts(db, [f.fact_id for f in facts])
        
        # Step 5: Separate supporting vs conflicting evidence
        conflicting_fact_ids = set()
        for cg in result.conflicts:
            for item in cg.items:
                conflicting_fact_ids.add(item.fact_id)
        
        result.supporting_evidence = [
            e for e in result.all_evidence if e.fact_id not in conflicting_fact_ids
        ]
        
        # Count unique source documents
        doc_ids = set(e.document_id for e in result.all_evidence)
        result.total_sources = len(doc_ids)
        
        logger.info(
            f"Assembled {len(result.all_evidence)} evidence items, "
            f"{len(result.conflicts)} conflict groups from {result.total_sources} sources"
        )
        
        return result

    async def _find_matching_entities(
        self, db: AsyncSession, analysis: QueryAnalysis
    ) -> list[str]:
        """Find entity IDs matching the query's identified entities."""
        entity_ids = []
        
        for entity_ref in analysis.identified_entities + analysis.component_ids:
            # Search by canonical name
            stmt = select(Entity).where(
                Entity.canonical_name.ilike(f"%{entity_ref}%")
            )
            result = await db.execute(stmt)
            entities = result.scalars().all()
            
            for e in entities:
                if e.entity_id not in entity_ids:
                    entity_ids.append(e.entity_id)
            
            # Search by alias
            stmt = select(EntityAlias).where(
                EntityAlias.alias_text.ilike(f"%{entity_ref}%")
            )
            result = await db.execute(stmt)
            aliases = result.scalars().all()
            
            for a in aliases:
                if a.entity_id not in entity_ids:
                    entity_ids.append(a.entity_id)
        
        logger.debug(f"Found {len(entity_ids)} matching entities")
        return entity_ids

    async def _find_relevant_facts(
        self, db: AsyncSession, entity_ids: list[str], analysis: QueryAnalysis
    ) -> list[Fact]:
        """Find facts relevant to the query."""
        facts = []
        
        # By entity
        if entity_ids:
            stmt = (
                select(Fact)
                .where(Fact.subject_entity_id.in_(entity_ids))
                .options(selectinload(Fact.evidence_items))
            )
            result = await db.execute(stmt)
            facts.extend(result.scalars().all())
        
        # By predicate keywords
        for predicate in analysis.identified_predicates:
            stmt = (
                select(Fact)
                .where(Fact.predicate.ilike(f"%{predicate}%"))
                .options(selectinload(Fact.evidence_items))
            )
            result = await db.execute(stmt)
            for f in result.scalars().all():
                if f not in facts:
                    facts.append(f)
        
        # By general keywords if we don't have enough results
        if len(facts) < 3:
            for kw in analysis.keywords[:5]:
                stmt = (
                    select(Fact)
                    .where(
                        (Fact.predicate.ilike(f"%{kw}%")) |
                        (Fact.value.ilike(f"%{kw}%"))
                    )
                    .options(selectinload(Fact.evidence_items))
                    .limit(10)
                )
                result = await db.execute(stmt)
                for f in result.scalars().all():
                    if f not in facts:
                        facts.append(f)
        
        logger.debug(f"Found {len(facts)} relevant facts")
        return facts

    async def _load_evidence_for_fact(
        self, db: AsyncSession, fact: Fact
    ) -> list[EvidenceItem]:
        """Load all evidence items for a fact with document details."""
        items = []
        
        stmt = (
            select(Evidence)
            .where(Evidence.fact_id == fact.fact_id)
            .options(selectinload(Evidence.document))
        )
        result = await db.execute(stmt)
        evidence_records = result.scalars().all()
        
        # Get subject entity name
        subject_name = "Unknown"
        if fact.subject_entity_id:
            stmt = select(Entity).where(Entity.entity_id == fact.subject_entity_id)
            result = await db.execute(stmt)
            entity = result.scalar_one_or_none()
            if entity:
                subject_name = entity.canonical_name
        
        for ev in evidence_records:
            doc = ev.document
            items.append(EvidenceItem(
                fact_id=fact.fact_id,
                subject=subject_name,
                predicate=fact.predicate,
                value=fact.value,
                unit=fact.unit,
                document_name=doc.filename if doc else "Unknown",
                document_id=doc.document_id if doc else "",
                page_number=ev.page_number,
                section=ev.section,
                source_text=ev.source_text,
                trust_level=doc.trust_level.value if doc else "unknown",
                confidence=fact.confidence,
                extraction_method=fact.extraction_method.value if fact.extraction_method else "unknown",
                revision_scope=fact.revision_scope,
                verification_status=fact.verification_status.value if fact.verification_status else "unverified",
                valid_from=fact.valid_from,
                valid_to=fact.valid_to,
            ))
        
        # If no evidence records but fact exists, create a basic item
        if not evidence_records:
            items.append(EvidenceItem(
                fact_id=fact.fact_id,
                subject=subject_name,
                predicate=fact.predicate,
                value=fact.value,
                unit=fact.unit,
                document_name="Unknown",
                document_id="",
                page_number=None,
                section=None,
                source_text=None,
                trust_level="unknown",
                confidence=fact.confidence,
                extraction_method=fact.extraction_method.value if fact.extraction_method else "unknown",
                revision_scope=fact.revision_scope,
                verification_status=fact.verification_status.value if fact.verification_status else "unverified",
            ))
        
        return items

    async def _find_conflicts(
        self, db: AsyncSession, fact_ids: list[str]
    ) -> list[ConflictGroup]:
        """Find conflicts involving the given facts."""
        if not fact_ids:
            return []
        
        groups = []
        
        # Find conflicts linked to our facts
        stmt = (
            select(Conflict)
            .join(conflict_facts)
            .where(conflict_facts.c.fact_id.in_(fact_ids))
            .options(selectinload(Conflict.facts))
        )
        result = await db.execute(stmt)
        conflicts = result.scalars().unique().all()
        
        for conflict in conflicts:
            group = ConflictGroup(
                conflict_id=conflict.conflict_id,
                conflict_type=conflict.conflict_type.value if conflict.conflict_type else "unknown",
                resolution_status=conflict.resolution_status.value if conflict.resolution_status else "unresolved",
                explanation=conflict.explanation,
            )
            
            # Load evidence for each fact in the conflict
            for fact in conflict.facts:
                items = await self._load_evidence_for_fact(db, fact)
                group.items.extend(items)
            
            groups.append(group)
        
        return groups
