"""Pydantic v2 schemas for request and response validation in Aegis Knowledge System."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.knowledge.models import (
    ConflictType,
    DocumentType,
    EntityType,
    ExtractionMethod,
    ExtractionStatus,
    RelationshipType,
    ResolutionMethod,
    ResolutionStatus,
    TrustLevel,
    VerificationStatus,
    generate_uuid,
)


# ============================================================================
# Document Chunk Schemas
# ============================================================================

class DocumentChunkBase(BaseModel):
    chunk_index: int
    content: str
    page_number: Optional[int] = None
    section_header: Optional[str] = None
    token_count: Optional[int] = 0
    meta_info: Dict[str, Any] = Field(default_factory=dict)


class DocumentChunkCreate(DocumentChunkBase):
    document_id: str


class DocumentChunkResponse(DocumentChunkBase):
    chunk_id: str
    document_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Document Schemas
# ============================================================================

class DocumentBase(BaseModel):
    filename: str
    file_path: str
    doc_type: DocumentType = DocumentType.TEXT
    doc_title: Optional[str] = None
    revision: Optional[str] = None
    source_system: Optional[str] = None
    trust_level: TrustLevel = TrustLevel.MEDIUM
    file_size_bytes: Optional[int] = 0
    meta_info: Dict[str, Any] = Field(default_factory=dict)


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    doc_title: Optional[str] = None
    revision: Optional[str] = None
    source_system: Optional[str] = None
    trust_level: Optional[TrustLevel] = None
    extraction_status: Optional[ExtractionStatus] = None
    error_message: Optional[str] = None
    chunk_count: Optional[int] = None
    fact_count: Optional[int] = None
    meta_info: Optional[Dict[str, Any]] = None


class DocumentResponse(DocumentBase):
    document_id: str
    extraction_status: ExtractionStatus
    file_size_bytes: Optional[int] = 0
    chunk_count: int = 0
    fact_count: int = 0
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentDetailResponse(DocumentResponse):
    chunks: List[DocumentChunkResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Entity Alias Schemas
# ============================================================================

class EntityAliasBase(BaseModel):
    alias_name: str
    resolution_method: ResolutionMethod = ResolutionMethod.EXACT
    confidence_score: float = 1.0


class EntityAliasCreate(EntityAliasBase):
    entity_id: str


class EntityAliasResponse(EntityAliasBase):
    alias_id: str
    entity_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Entity Schemas
# ============================================================================

class EntityBase(BaseModel):
    canonical_name: str
    entity_type: EntityType = EntityType.COMPONENT
    description: Optional[str] = None
    system_context: Optional[str] = None
    meta_info: Dict[str, Any] = Field(default_factory=dict)


class EntityCreate(EntityBase):
    aliases: List[str] = Field(default_factory=list)


class EntityResponse(EntityBase):
    entity_id: str
    created_at: datetime
    updated_at: datetime
    aliases: List[EntityAliasResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Evidence Schemas
# ============================================================================

class EvidenceBase(BaseModel):
    fact_id: str
    document_id: str
    snippet: str
    chunk_id: Optional[str] = None
    page_number: Optional[int] = None
    confidence_score: float = 1.0
    extraction_method: ExtractionMethod = ExtractionMethod.PATTERN
    meta_info: Dict[str, Any] = Field(default_factory=dict)


class EvidenceCreate(EvidenceBase):
    pass


class EvidenceResponse(EvidenceBase):
    evidence_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Fact Schemas
# ============================================================================

class FactBase(BaseModel):
    entity_id: str
    predicate: str
    value: str
    unit: Optional[str] = None
    data_type: str = "string"
    numeric_value: Optional[float] = None
    tolerance_min: Optional[float] = None
    tolerance_max: Optional[float] = None
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    confidence_score: float = 1.0
    is_current: bool = True
    meta_info: Dict[str, Any] = Field(default_factory=dict)


class FactCreate(FactBase):
    evidence_snippet: Optional[str] = None
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    page_number: Optional[int] = None
    extraction_method: Optional[ExtractionMethod] = ExtractionMethod.PATTERN


class FactUpdate(BaseModel):
    value: Optional[str] = None
    unit: Optional[str] = None
    data_type: Optional[str] = None
    numeric_value: Optional[float] = None
    tolerance_min: Optional[float] = None
    tolerance_max: Optional[float] = None
    verification_status: Optional[VerificationStatus] = None
    confidence_score: Optional[float] = None
    is_current: Optional[bool] = None
    meta_info: Optional[Dict[str, Any]] = None


class FactResponse(FactBase):
    fact_id: str
    created_at: datetime
    updated_at: datetime
    evidence: List[EvidenceResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Conflict Schemas
# ============================================================================

class ConflictBase(BaseModel):
    predicate: str
    description: str
    conflict_type: ConflictType = ConflictType.VALUE_MISMATCH
    status: ResolutionStatus = ResolutionStatus.UNRESOLVED
    resolution_notes: Optional[str] = None
    resolution_method: Optional[ResolutionMethod] = None
    resolved_by: Optional[str] = None
    meta_info: Dict[str, Any] = Field(default_factory=dict)


class ConflictCreate(ConflictBase):
    fact_ids: List[str] = Field(default_factory=list)


class ConflictResolveRequest(BaseModel):
    status: ResolutionStatus = ResolutionStatus.RESOLVED_BY_REVISION
    resolution_notes: str
    resolution_method: ResolutionMethod = ResolutionMethod.NORMALIZED
    resolved_by: str = "system"


class ConflictResponse(ConflictBase):
    conflict_id: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    facts: List[FactResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Relationship Schemas
# ============================================================================

class RelationshipBase(BaseModel):
    source_entity_id: str
    target_entity_id: str
    relation_type: RelationshipType
    weight: float = 1.0
    description: Optional[str] = None
    meta_info: Dict[str, Any] = Field(default_factory=dict)


class RelationshipCreate(RelationshipBase):
    pass


class RelationshipResponse(RelationshipBase):
    relationship_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Detailed Entity Response with related facts and relationships
class EntityDetailResponse(EntityResponse):
    facts: List[FactResponse] = Field(default_factory=list)
    outgoing_relationships: List[RelationshipResponse] = Field(default_factory=list)
    incoming_relationships: List[RelationshipResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Query and Answer Grounding Schemas
# ============================================================================

class Claim(BaseModel):
    claim_id: str = Field(default_factory=generate_uuid)
    entity_name: str
    predicate: str
    value: str
    unit: Optional[str] = None
    status: str = "unverified"
    confidence: float = 1.0
    source_doc: Optional[str] = None


class EvidenceItem(BaseModel):
    evidence_id: str = Field(default_factory=generate_uuid)
    fact_id: Optional[str] = None
    document_name: Optional[str] = None
    snippet: str
    page_number: Optional[int] = None
    confidence_score: float = 1.0
    extraction_method: str = "pattern"


class ConflictInfo(BaseModel):
    conflict_id: str
    predicate: str
    description: str
    conflict_type: str
    status: str
    conflicting_values: List[str] = Field(default_factory=list)
    resolution_notes: Optional[str] = None


class QueryRequest(BaseModel):
    question: str
    top_k: int = Field(default=5, ge=1, le=50)
    include_conflicts: bool = True
    entity_filter: Optional[str] = None
    confidence_threshold: float = Field(default=0.0, ge=0.0, le=1.0)


class QueryResponse(BaseModel):
    question: str
    answer: str
    confidence: float
    claims: List[Claim] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    conflicts: List[ConflictInfo] = Field(default_factory=list)
    query_time_ms: float = 0.0
    status: str = "success"


# ============================================================================
# Ingestion Schemas
# ============================================================================

class IngestionStatusResponse(BaseModel):
    status: str
    total_documents: int
    completed_documents: int
    failed_documents: int
    total_chunks: int
    total_facts: int
    total_conflicts: int
    active_jobs: int = 0
    last_ingested_at: Optional[datetime] = None


class IngestionReportResponse(BaseModel):
    job_id: str = Field(default_factory=generate_uuid)
    status: str
    documents_processed: int
    documents_failed: int
    total_chunks_created: int
    total_facts_extracted: int
    total_conflicts_identified: int
    processing_time_seconds: float
    details: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


# ============================================================================
# Evaluation Schemas
# ============================================================================

class EvaluationRequest(BaseModel):
    eval_dataset_path: Optional[str] = None
    sample_size: Optional[int] = Field(default=10, ge=1, le=100)
    include_conflicts: bool = True


class QuestionResult(BaseModel):
    question_id: str = Field(default_factory=generate_uuid)
    question: str
    expected_answer: Optional[str] = None
    generated_answer: str
    accuracy_score: float
    evidence_grounding_score: float
    latency_ms: float
    claims_count: int
    conflicts_detected: int
    passed: bool


class EvaluationMetrics(BaseModel):
    total_questions: int
    passed_questions: int
    accuracy: float
    evidence_grounding_ratio: float
    conflict_detection_rate: float
    avg_latency_ms: float


class EvaluationResponse(BaseModel):
    run_id: str = Field(default_factory=generate_uuid)
    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metrics: EvaluationMetrics
    results: List[QuestionResult] = Field(default_factory=list)
