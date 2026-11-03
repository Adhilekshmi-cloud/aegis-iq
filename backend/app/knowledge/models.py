"""SQLAlchemy ORM models for Aegis Knowledge System."""

import enum
import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    """Generate a random UUID4 string."""
    return str(uuid.uuid4())


class DocumentType(str, enum.Enum):
    PDF = "pdf"
    SCANNED_PDF = "scanned_pdf"
    HTML = "html"
    XLSX = "xlsx"
    DOCX = "docx"
    PNG = "png"
    JSON_DOC = "json"
    PPTX = "pptx"
    MARKDOWN = "markdown"
    TEXT = "text"


class TrustLevel(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExtractionStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class EntityType(str, enum.Enum):
    COMPONENT = "component"
    SYSTEM = "system"
    SUBSYSTEM = "subsystem"
    PARAMETER = "parameter"
    MATERIAL = "material"
    FLUID = "fluid"
    TOOL = "tool"
    DOCUMENT_REF = "document_ref"


class ExtractionMethod(str, enum.Enum):
    RULE = "rule"
    PATTERN = "pattern"
    TABLE = "table"
    LLM = "llm"
    MANUAL = "manual"


class VerificationStatus(str, enum.Enum):
    VERIFIED = "verified"
    CONFLICTING = "conflicting"
    UNVERIFIED = "unverified"
    SUPERSEDED = "superseded"


class ConflictType(str, enum.Enum):
    VALUE_MISMATCH = "value_mismatch"
    VERSION_DIFFERENCE = "version_difference"
    SOURCE_DISAGREEMENT = "source_disagreement"


class ResolutionStatus(str, enum.Enum):
    UNRESOLVED = "unresolved"
    RESOLVED_BY_REVISION = "resolved_by_revision"
    RESOLVED_BY_TRUST = "resolved_by_trust"
    NEEDS_REVIEW = "needs_review"


class ResolutionMethod(str, enum.Enum):
    EXACT = "exact"
    NORMALIZED = "normalized"
    FUZZY = "fuzzy"
    MODEL = "model"
    HMI_MAPPING = "hmi_mapping"


class RelationshipType(str, enum.Enum):
    CONTAINS = "contains"
    CONNECTS_TO = "connects_to"
    CONTROLS = "controls"
    MONITORS = "monitors"
    REPLACES = "replaces"
    VARIANT_OF = "variant_of"
    PART_OF = "part_of"


# M2M table for Conflict <-> Fact
conflict_facts = Table(
    "conflict_facts",
    Base.metadata,
    Column(
        "conflict_id",
        String,
        ForeignKey("conflicts.conflict_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "fact_id",
        String,
        ForeignKey("facts.fact_id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Document(Base):
    """Document model representing an ingested file in the system."""

    __tablename__ = "documents"

    document_id = Column(String, primary_key=True, default=generate_uuid)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False, unique=True)
    doc_type = Column(Enum(DocumentType), default=DocumentType.TEXT, nullable=False)
    doc_title = Column(String, nullable=True)
    revision = Column(String, nullable=True)
    source_system = Column(String, nullable=True)
    trust_level = Column(Enum(TrustLevel), default=TrustLevel.MEDIUM, nullable=False)
    extraction_status = Column(
        Enum(ExtractionStatus), default=ExtractionStatus.PENDING, nullable=False
    )
    file_size_bytes = Column(Integer, nullable=True, default=0)
    chunk_count = Column(Integer, default=0, nullable=False)
    fact_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    meta_info = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    evidence_items = relationship(
        "Evidence",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Document(document_id='{self.document_id}', filename='{self.filename}', status='{self.extraction_status}')>"


class DocumentChunk(Base):
    """Document chunk model representing partitioned text content."""

    __tablename__ = "document_chunks"

    chunk_id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(
        String,
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    section_header = Column(String, nullable=True)
    token_count = Column(Integer, nullable=True, default=0)
    meta_info = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="chunks")
    evidence_items = relationship("Evidence", back_populates="chunk")

    def __repr__(self) -> str:
        return f"<DocumentChunk(chunk_id='{self.chunk_id}', document_id='{self.document_id}', index={self.chunk_index})>"


class Entity(Base):
    """Core knowledge entity (component, system, tool, etc.)."""

    __tablename__ = "entities"

    entity_id = Column(String, primary_key=True, default=generate_uuid)
    canonical_name = Column(String, nullable=False, unique=True, index=True)
    entity_type = Column(
        Enum(EntityType), default=EntityType.COMPONENT, nullable=False, index=True
    )
    description = Column(Text, nullable=True)
    system_context = Column(String, nullable=True)
    meta_info = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    aliases = relationship(
        "EntityAlias",
        back_populates="entity",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    facts = relationship(
        "Fact",
        back_populates="entity",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="Fact.entity_id",
    )
    outgoing_relationships = relationship(
        "Relationship",
        foreign_keys="Relationship.source_entity_id",
        back_populates="source_entity",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    incoming_relationships = relationship(
        "Relationship",
        foreign_keys="Relationship.target_entity_id",
        back_populates="target_entity",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Entity(entity_id='{self.entity_id}', canonical_name='{self.canonical_name}', type='{self.entity_type}')>"


class EntityAlias(Base):
    """Alternative naming/identifier alias for an entity."""

    __tablename__ = "entity_aliases"

    alias_id = Column(String, primary_key=True, default=generate_uuid)
    entity_id = Column(
        String,
        ForeignKey("entities.entity_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alias_name = Column(String, nullable=False, index=True)
    resolution_method = Column(
        Enum(ResolutionMethod), default=ResolutionMethod.EXACT, nullable=False
    )
    confidence_score = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    entity = relationship("Entity", back_populates="aliases")

    def __repr__(self) -> str:
        return f"<EntityAlias(alias_id='{self.alias_id}', alias_name='{self.alias_name}', entity_id='{self.entity_id}')>"


class Fact(Base):
    """Extracted engineering fact or parameter specification."""

    __tablename__ = "facts"

    fact_id = Column(String, primary_key=True, default=generate_uuid)
    entity_id = Column(
        String,
        ForeignKey("entities.entity_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    predicate = Column(String, nullable=False, index=True)
    value = Column(Text, nullable=False)
    unit = Column(String, nullable=True)
    data_type = Column(String, default="string", nullable=False)
    numeric_value = Column(Float, nullable=True)
    tolerance_min = Column(Float, nullable=True)
    tolerance_max = Column(Float, nullable=True)
    verification_status = Column(
        Enum(VerificationStatus),
        default=VerificationStatus.UNVERIFIED,
        nullable=False,
        index=True,
    )
    confidence_score = Column(Float, default=1.0, nullable=False)
    is_current = Column(Boolean, default=True, nullable=False)
    meta_info = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    entity = relationship("Entity", back_populates="facts")
    evidence = relationship(
        "Evidence",
        back_populates="fact",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    conflicts = relationship(
        "Conflict",
        secondary=conflict_facts,
        back_populates="facts",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Fact(fact_id='{self.fact_id}', predicate='{self.predicate}', value='{self.value}', status='{self.verification_status}')>"


class Evidence(Base):
    """Source grounded evidence linking a fact to a document snippet."""

    __tablename__ = "evidence"

    evidence_id = Column(String, primary_key=True, default=generate_uuid)
    fact_id = Column(
        String,
        ForeignKey("facts.fact_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id = Column(
        String,
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id = Column(
        String,
        ForeignKey("document_chunks.chunk_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    snippet = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    confidence_score = Column(Float, default=1.0, nullable=False)
    extraction_method = Column(
        Enum(ExtractionMethod), default=ExtractionMethod.PATTERN, nullable=False
    )
    meta_info = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    fact = relationship("Fact", back_populates="evidence")
    document = relationship("Document", back_populates="evidence_items")
    chunk = relationship("DocumentChunk", back_populates="evidence_items")

    def __repr__(self) -> str:
        return f"<Evidence(evidence_id='{self.evidence_id}', fact_id='{self.fact_id}', doc_id='{self.document_id}')>"


class Conflict(Base):
    """Discrepancy or conflict detected between multiple facts."""

    __tablename__ = "conflicts"

    conflict_id = Column(String, primary_key=True, default=generate_uuid)
    conflict_type = Column(
        Enum(ConflictType), default=ConflictType.VALUE_MISMATCH, nullable=False
    )
    predicate = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    status = Column(
        Enum(ResolutionStatus),
        default=ResolutionStatus.UNRESOLVED,
        nullable=False,
        index=True,
    )
    resolution_notes = Column(Text, nullable=True)
    resolution_method = Column(Enum(ResolutionMethod), nullable=True)
    resolved_by = Column(String, nullable=True)
    meta_info = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    facts = relationship(
        "Fact",
        secondary=conflict_facts,
        back_populates="conflicts",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Conflict(conflict_id='{self.conflict_id}', type='{self.conflict_type}', status='{self.status}')>"


class Relationship(Base):
    """Directed relationship between two knowledge entities."""

    __tablename__ = "relationships"

    relationship_id = Column(String, primary_key=True, default=generate_uuid)
    source_entity_id = Column(
        String,
        ForeignKey("entities.entity_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_entity_id = Column(
        String,
        ForeignKey("entities.entity_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_type = Column(Enum(RelationshipType), nullable=False, index=True)
    weight = Column(Float, default=1.0, nullable=False)
    description = Column(Text, nullable=True)
    meta_info = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    source_entity = relationship(
        "Entity",
        foreign_keys=[source_entity_id],
        back_populates="outgoing_relationships",
    )
    target_entity = relationship(
        "Entity",
        foreign_keys=[target_entity_id],
        back_populates="incoming_relationships",
    )

    def __repr__(self) -> str:
        return f"<Relationship(id='{self.relationship_id}', type='{self.relation_type}', src='{self.source_entity_id}', tgt='{self.target_entity_id}')>"
