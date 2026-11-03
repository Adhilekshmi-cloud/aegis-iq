"""Asynchronous CRUD repositories for Aegis Knowledge System."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.knowledge.models import (
    Conflict,
    ConflictType,
    Document,
    DocumentChunk,
    DocumentType,
    Entity,
    EntityAlias,
    EntityType,
    Evidence,
    ExtractionMethod,
    ExtractionStatus,
    Fact,
    Relationship,
    RelationshipType,
    ResolutionMethod,
    ResolutionStatus,
    TrustLevel,
    VerificationStatus,
    conflict_facts,
    generate_uuid,
)
from app.knowledge.schemas import (
    ConflictCreate,
    DocumentChunkCreate,
    DocumentCreate,
    DocumentUpdate,
    EntityCreate,
    EvidenceCreate,
    FactCreate,
    FactUpdate,
    RelationshipCreate,
)

logger = logging.getLogger(__name__)


class DocumentRepository:
    """Repository handling database operations for documents."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, doc_data: Union[DocumentCreate, Dict[str, Any]]) -> Document:
        """Create and persist a new Document."""
        data = doc_data.model_dump() if isinstance(doc_data, DocumentCreate) else dict(doc_data)
        document = Document(
            document_id=data.get("document_id") or generate_uuid(),
            filename=data["filename"],
            file_path=data["file_path"],
            doc_type=data.get("doc_type", DocumentType.TEXT),
            doc_title=data.get("doc_title"),
            revision=data.get("revision"),
            source_system=data.get("source_system"),
            trust_level=data.get("trust_level", TrustLevel.MEDIUM),
            extraction_status=data.get("extraction_status", ExtractionStatus.PENDING),
            file_size_bytes=data.get("file_size_bytes", 0),
            meta_info=data.get("meta_info", {}),
        )
        self.session.add(document)
        await self.session.flush()
        await self.session.refresh(document)
        logger.info("Created document record: %s (id: %s)", document.filename, document.document_id)
        return document

    async def get(self, document_id: str) -> Optional[Document]:
        """Fetch a document by its primary key with chunks loaded."""
        stmt = (
            select(Document)
            .where(Document.document_id == document_id)
            .options(selectinload(Document.chunks), selectinload(Document.evidence_items))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_path(self, file_path: str) -> Optional[Document]:
        """Fetch a document by its file path."""
        stmt = select(Document).where(Document.file_path == file_path)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[ExtractionStatus] = None,
    ) -> List[Document]:
        """Fetch a list of documents with optional status filtering."""
        stmt = select(Document).order_by(Document.created_at.desc()).offset(skip).limit(limit)
        if status:
            stmt = stmt.where(Document.extraction_status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        document_id: str,
        status: ExtractionStatus,
        error_message: Optional[str] = None,
        chunk_count: Optional[int] = None,
        fact_count: Optional[int] = None,
    ) -> Optional[Document]:
        """Update the extraction status and counts for a document."""
        document = await self.get(document_id)
        if not document:
            return None
        document.extraction_status = status
        if error_message is not None:
            document.error_message = error_message
        if chunk_count is not None:
            document.chunk_count = chunk_count
        if fact_count is not None:
            document.fact_count = fact_count
        document.updated_at = datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(document)
        logger.info("Updated document %s status to %s", document_id, status)
        return document

    async def delete(self, document_id: str) -> bool:
        """Delete a document by ID."""
        document = await self.get(document_id)
        if not document:
            return False
        await self.session.delete(document)
        await self.session.flush()
        return True

    async def count(self, status: Optional[ExtractionStatus] = None) -> int:
        """Count total documents matching optional status."""
        stmt = select(func.count(Document.document_id))
        if status:
            stmt = stmt.where(Document.extraction_status == status)
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)


class ChunkRepository:
    """Repository handling chunk storage and textual retrieval."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, chunk_data: Union[DocumentChunkCreate, Dict[str, Any]]
    ) -> DocumentChunk:
        """Store a single document chunk."""
        data = (
            chunk_data.model_dump()
            if isinstance(chunk_data, DocumentChunkCreate)
            else dict(chunk_data)
        )
        chunk = DocumentChunk(
            chunk_id=data.get("chunk_id") or generate_uuid(),
            document_id=data["document_id"],
            chunk_index=data["chunk_index"],
            content=data["content"],
            page_number=data.get("page_number"),
            section_header=data.get("section_header"),
            token_count=data.get("token_count", 0),
            meta_info=data.get("meta_info", {}),
        )
        self.session.add(chunk)
        await self.session.flush()
        await self.session.refresh(chunk)
        return chunk

    async def create_batch(
        self, chunks_data: List[Union[DocumentChunkCreate, Dict[str, Any]]]
    ) -> List[DocumentChunk]:
        """Store multiple chunks in a single operation."""
        chunks: List[DocumentChunk] = []
        for c in chunks_data:
            data = c.model_dump() if isinstance(c, DocumentChunkCreate) else dict(c)
            chunk = DocumentChunk(
                chunk_id=data.get("chunk_id") or generate_uuid(),
                document_id=data["document_id"],
                chunk_index=data["chunk_index"],
                content=data["content"],
                page_number=data.get("page_number"),
                section_header=data.get("section_header"),
                token_count=data.get("token_count", 0),
                meta_info=data.get("meta_info", {}),
            )
            self.session.add(chunk)
            chunks.append(chunk)
        await self.session.flush()
        return chunks

    async def get(self, chunk_id: str) -> Optional[DocumentChunk]:
        """Get a chunk by its chunk_id."""
        stmt = select(DocumentChunk).where(DocumentChunk.chunk_id == chunk_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_document(
        self, document_id: str, skip: int = 0, limit: int = 100
    ) -> List[DocumentChunk]:
        """Fetch all chunks belonging to a document ordered by index."""
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_text(self, query: str, limit: int = 10) -> List[DocumentChunk]:
        """Perform substring search across chunk contents."""
        term = f"%{query.strip()}%"
        stmt = (
            select(DocumentChunk)
            .where(
                or_(
                    DocumentChunk.content.ilike(term),
                    DocumentChunk.section_header.ilike(term),
                )
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, document_id: Optional[str] = None) -> int:
        """Count chunks, optionally filtered by document."""
        stmt = select(func.count(DocumentChunk.chunk_id))
        if document_id:
            stmt = stmt.where(DocumentChunk.document_id == document_id)
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)


class EntityRepository:
    """Repository handling knowledge graph entities and their aliases."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, entity_data: Union[EntityCreate, Dict[str, Any]]) -> Entity:
        """Create a new entity with optional initial aliases."""
        data = (
            entity_data.model_dump()
            if isinstance(entity_data, EntityCreate)
            else dict(entity_data)
        )
        canonical = data["canonical_name"].strip()
        existing = await self.get_by_name(canonical)
        if existing:
            return existing

        entity = Entity(
            entity_id=data.get("entity_id") or generate_uuid(),
            canonical_name=canonical,
            entity_type=data.get("entity_type", EntityType.COMPONENT),
            description=data.get("description"),
            system_context=data.get("system_context"),
            meta_info=data.get("meta_info", {}),
        )
        self.session.add(entity)
        await self.session.flush()

        # Add initial aliases if provided
        raw_aliases = data.get("aliases", [])
        for alias_str in raw_aliases:
            if alias_str and alias_str.strip().lower() != canonical.lower():
                alias = EntityAlias(
                    alias_id=generate_uuid(),
                    entity_id=entity.entity_id,
                    alias_name=alias_str.strip(),
                    resolution_method=ResolutionMethod.EXACT,
                    confidence_score=1.0,
                )
                self.session.add(alias)

        await self.session.flush()
        await self.session.refresh(entity)
        logger.info("Created entity: %s (id: %s)", entity.canonical_name, entity.entity_id)
        return entity

    async def get(self, entity_id: str) -> Optional[Entity]:
        """Fetch an entity by ID including aliases and facts."""
        stmt = (
            select(Entity)
            .where(Entity.entity_id == entity_id)
            .options(
                selectinload(Entity.aliases),
                selectinload(Entity.facts).selectinload(Fact.evidence),
                selectinload(Entity.outgoing_relationships),
                selectinload(Entity.incoming_relationships),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, canonical_name: str) -> Optional[Entity]:
        """Fetch an entity by exact or normalized canonical name."""
        stmt = (
            select(Entity)
            .where(func.lower(Entity.canonical_name) == canonical_name.strip().lower())
            .options(selectinload(Entity.aliases), selectinload(Entity.facts))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        entity_type: Optional[EntityType] = None,
    ) -> List[Entity]:
        """Fetch all entities with optional type filter."""
        stmt = (
            select(Entity)
            .options(selectinload(Entity.aliases))
            .order_by(Entity.canonical_name.asc())
            .offset(skip)
            .limit(limit)
        )
        if entity_type:
            stmt = stmt.where(Entity.entity_type == entity_type)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_alias(
        self,
        entity_id: str,
        alias_name: str,
        method: ResolutionMethod = ResolutionMethod.EXACT,
        score: float = 1.0,
    ) -> Optional[EntityAlias]:
        """Register an alias for an existing entity."""
        clean_alias = alias_name.strip()
        # Check if alias already exists for this entity
        check_stmt = select(EntityAlias).where(
            EntityAlias.entity_id == entity_id,
            func.lower(EntityAlias.alias_name) == clean_alias.lower(),
        )
        existing = (await self.session.execute(check_stmt)).scalar_one_or_none()
        if existing:
            return existing

        alias = EntityAlias(
            alias_id=generate_uuid(),
            entity_id=entity_id,
            alias_name=clean_alias,
            resolution_method=method,
            confidence_score=score,
        )
        self.session.add(alias)
        await self.session.flush()
        await self.session.refresh(alias)
        return alias

    async def search(self, query: str, limit: int = 20) -> List[Entity]:
        """Search entities by canonical name or alias match."""
        term = f"%{query.strip().lower()}%"
        stmt = (
            select(Entity)
            .outerjoin(EntityAlias, Entity.entity_id == EntityAlias.entity_id)
            .where(
                or_(
                    func.lower(Entity.canonical_name).ilike(term),
                    func.lower(EntityAlias.alias_name).ilike(term),
                    func.lower(Entity.description).ilike(term),
                )
            )
            .options(selectinload(Entity.aliases))
            .distinct()
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        """Count total entities."""
        stmt = select(func.count(Entity.entity_id))
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)


class FactRepository:
    """Repository handling knowledge facts and parameter assertions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, fact_data: Union[FactCreate, Dict[str, Any]]) -> Fact:
        """Create and store a Fact along with optional initial Evidence."""
        data = fact_data.model_dump() if isinstance(fact_data, FactCreate) else dict(fact_data)
        fact = Fact(
            fact_id=data.get("fact_id") or generate_uuid(),
            entity_id=data["entity_id"],
            predicate=data["predicate"].strip(),
            value=data["value"].strip(),
            unit=data.get("unit"),
            data_type=data.get("data_type", "string"),
            numeric_value=data.get("numeric_value"),
            tolerance_min=data.get("tolerance_min"),
            tolerance_max=data.get("tolerance_max"),
            verification_status=data.get(
                "verification_status", VerificationStatus.UNVERIFIED
            ),
            confidence_score=data.get("confidence_score", 1.0),
            is_current=data.get("is_current", True),
            meta_info=data.get("meta_info", {}),
        )
        self.session.add(fact)
        await self.session.flush()

        # Add initial evidence if provided
        snippet = data.get("evidence_snippet")
        doc_id = data.get("document_id")
        if snippet and doc_id:
            evidence = Evidence(
                evidence_id=generate_uuid(),
                fact_id=fact.fact_id,
                document_id=doc_id,
                chunk_id=data.get("chunk_id"),
                snippet=snippet,
                page_number=data.get("page_number"),
                confidence_score=fact.confidence_score,
                extraction_method=data.get(
                    "extraction_method", ExtractionMethod.PATTERN
                ),
            )
            self.session.add(evidence)
            await self.session.flush()

        await self.session.refresh(fact)
        logger.info(
            "Created fact: %s -> %s = %s (id: %s)",
            fact.entity_id,
            fact.predicate,
            fact.value,
            fact.fact_id,
        )
        return fact

    async def get(self, fact_id: str) -> Optional[Fact]:
        """Fetch a fact by ID with evidence and conflicts loaded."""
        stmt = (
            select(Fact)
            .where(Fact.fact_id == fact_id)
            .options(
                selectinload(Fact.evidence),
                selectinload(Fact.conflicts),
                selectinload(Fact.entity),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_entity(
        self, entity_id: str, is_current: Optional[bool] = None
    ) -> List[Fact]:
        """Fetch all facts associated with an entity."""
        stmt = (
            select(Fact)
            .where(Fact.entity_id == entity_id)
            .options(selectinload(Fact.evidence))
            .order_by(Fact.predicate.asc())
        )
        if is_current is not None:
            stmt = stmt.where(Fact.is_current == is_current)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_predicate(
        self, predicate: str, entity_id: Optional[str] = None
    ) -> List[Fact]:
        """Fetch facts matching a specific predicate name."""
        stmt = (
            select(Fact)
            .where(func.lower(Fact.predicate) == predicate.strip().lower())
            .options(selectinload(Fact.evidence))
        )
        if entity_id:
            stmt = stmt.where(Fact.entity_id == entity_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        entity_id: Optional[str] = None,
        predicate: Optional[str] = None,
        status: Optional[VerificationStatus] = None,
    ) -> List[Fact]:
        """List facts with optional filtering."""
        stmt = (
            select(Fact)
            .options(selectinload(Fact.evidence))
            .order_by(Fact.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if entity_id:
            stmt = stmt.where(Fact.entity_id == entity_id)
        if predicate:
            stmt = stmt.where(func.lower(Fact.predicate) == predicate.strip().lower())
        if status:
            stmt = stmt.where(Fact.verification_status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self, fact_id: str, update_data: Union[FactUpdate, Dict[str, Any]]
    ) -> Optional[Fact]:
        """Update an existing fact."""
        fact = await self.get(fact_id)
        if not fact:
            return None
        data = (
            update_data.model_dump(exclude_unset=True)
            if isinstance(update_data, FactUpdate)
            else dict(update_data)
        )
        for key, value in data.items():
            if hasattr(fact, key) and value is not None:
                setattr(fact, key, value)
        fact.updated_at = datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(fact)
        return fact

    async def count(self, status: Optional[VerificationStatus] = None) -> int:
        """Count facts, optionally filtered by status."""
        stmt = select(func.count(Fact.fact_id))
        if status:
            stmt = stmt.where(Fact.verification_status == status)
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)


class EvidenceRepository:
    """Repository handling source evidence items."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, evidence_data: Union[EvidenceCreate, Dict[str, Any]]
    ) -> Evidence:
        """Create a new evidence link."""
        data = (
            evidence_data.model_dump()
            if isinstance(evidence_data, EvidenceCreate)
            else dict(evidence_data)
        )
        evidence = Evidence(
            evidence_id=data.get("evidence_id") or generate_uuid(),
            fact_id=data["fact_id"],
            document_id=data["document_id"],
            chunk_id=data.get("chunk_id"),
            snippet=data["snippet"],
            page_number=data.get("page_number"),
            confidence_score=data.get("confidence_score", 1.0),
            extraction_method=data.get(
                "extraction_method", ExtractionMethod.PATTERN
            ),
            meta_info=data.get("meta_info", {}),
        )
        self.session.add(evidence)
        await self.session.flush()
        await self.session.refresh(evidence)
        return evidence

    async def get(self, evidence_id: str) -> Optional[Evidence]:
        """Fetch an evidence record by ID."""
        stmt = select(Evidence).where(Evidence.evidence_id == evidence_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_fact(self, fact_id: str) -> List[Evidence]:
        """Fetch all evidence records attached to a fact."""
        stmt = (
            select(Evidence)
            .where(Evidence.fact_id == fact_id)
            .order_by(Evidence.confidence_score.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_document(self, document_id: str) -> List[Evidence]:
        """Fetch all evidence records originating from a document."""
        stmt = select(Evidence).where(Evidence.document_id == document_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ConflictRepository:
    """Repository handling detected conflicts between facts."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, conflict_data: Union[ConflictCreate, Dict[str, Any]]
    ) -> Conflict:
        """Create a conflict record and associate conflicting facts."""
        data = (
            conflict_data.model_dump()
            if isinstance(conflict_data, ConflictCreate)
            else dict(conflict_data)
        )
        conflict = Conflict(
            conflict_id=data.get("conflict_id") or generate_uuid(),
            conflict_type=data.get("conflict_type", ConflictType.VALUE_MISMATCH),
            predicate=data["predicate"],
            description=data["description"],
            status=data.get("status", ResolutionStatus.UNRESOLVED),
            resolution_notes=data.get("resolution_notes"),
            resolution_method=data.get("resolution_method"),
            resolved_by=data.get("resolved_by"),
            meta_info=data.get("meta_info", {}),
        )
        self.session.add(conflict)
        await self.session.flush()

        # Link related facts
        fact_ids = data.get("fact_ids", [])
        if fact_ids:
            facts_stmt = select(Fact).where(Fact.fact_id.in_(fact_ids))
            facts_result = await self.session.execute(facts_stmt)
            facts = list(facts_result.scalars().all())
            conflict.facts.extend(facts)
            await self.session.flush()

        await self.session.refresh(conflict)
        logger.warning(
            "Created conflict: %s on predicate '%s' (id: %s)",
            conflict.conflict_type,
            conflict.predicate,
            conflict.conflict_id,
        )
        return conflict

    async def get(self, conflict_id: str) -> Optional[Conflict]:
        """Fetch a conflict by ID with linked facts."""
        stmt = (
            select(Conflict)
            .where(Conflict.conflict_id == conflict_id)
            .options(
                selectinload(Conflict.facts).selectinload(Fact.evidence),
                selectinload(Conflict.facts).selectinload(Fact.entity),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[ResolutionStatus] = None,
    ) -> List[Conflict]:
        """List conflicts with optional status filter."""
        stmt = (
            select(Conflict)
            .options(selectinload(Conflict.facts))
            .order_by(Conflict.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if status:
            stmt = stmt.where(Conflict.status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_fact(self, fact_id: str) -> List[Conflict]:
        """Get all conflicts that involve a specific fact."""
        stmt = (
            select(Conflict)
            .join(conflict_facts, Conflict.conflict_id == conflict_facts.c.conflict_id)
            .where(conflict_facts.c.fact_id == fact_id)
            .options(selectinload(Conflict.facts))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def resolve(
        self,
        conflict_id: str,
        resolution_notes: str,
        resolution_method: ResolutionMethod,
        resolved_by: str = "system",
        status: ResolutionStatus = ResolutionStatus.RESOLVED_BY_REVISION,
    ) -> Optional[Conflict]:
        """Mark a conflict as resolved with documentation."""
        conflict = await self.get(conflict_id)
        if not conflict:
            return None
        conflict.status = status
        conflict.resolution_notes = resolution_notes
        conflict.resolution_method = resolution_method
        conflict.resolved_by = resolved_by
        conflict.resolved_at = datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(conflict)
        logger.info("Resolved conflict %s via %s", conflict_id, resolution_method)
        return conflict

    async def count(self, status: Optional[ResolutionStatus] = None) -> int:
        """Count conflicts, optionally filtered by status."""
        stmt = select(func.count(Conflict.conflict_id))
        if status:
            stmt = stmt.where(Conflict.status == status)
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)


class RelationshipRepository:
    """Repository handling entity-to-entity relationships."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, rel_data: Union[RelationshipCreate, Dict[str, Any]]
    ) -> Relationship:
        """Create a relationship between two entities."""
        data = (
            rel_data.model_dump()
            if isinstance(rel_data, RelationshipCreate)
            else dict(rel_data)
        )
        rel = Relationship(
            relationship_id=data.get("relationship_id") or generate_uuid(),
            source_entity_id=data["source_entity_id"],
            target_entity_id=data["target_entity_id"],
            relation_type=data["relation_type"],
            weight=data.get("weight", 1.0),
            description=data.get("description"),
            meta_info=data.get("meta_info", {}),
        )
        self.session.add(rel)
        await self.session.flush()
        await self.session.refresh(rel)
        return rel

    async def get(self, relationship_id: str) -> Optional[Relationship]:
        """Fetch relationship by ID."""
        stmt = select(Relationship).where(Relationship.relationship_id == relationship_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_entity(
        self, entity_id: str, direction: str = "both"
    ) -> List[Relationship]:
        """Fetch relationships linked to an entity by direction ('incoming', 'outgoing', 'both')."""
        if direction == "outgoing":
            stmt = select(Relationship).where(Relationship.source_entity_id == entity_id)
        elif direction == "incoming":
            stmt = select(Relationship).where(Relationship.target_entity_id == entity_id)
        else:
            stmt = select(Relationship).where(
                or_(
                    Relationship.source_entity_id == entity_id,
                    Relationship.target_entity_id == entity_id,
                )
            )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        relation_type: Optional[RelationshipType] = None,
    ) -> List[Relationship]:
        """List relationships with optional type filter."""
        stmt = select(Relationship).offset(skip).limit(limit)
        if relation_type:
            stmt = stmt.where(Relationship.relation_type == relation_type)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
