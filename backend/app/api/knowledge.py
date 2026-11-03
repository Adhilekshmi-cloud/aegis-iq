"""Knowledge browsing and inspection endpoints for Aegis Knowledge System."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.knowledge.models import (
    EntityType,
    ExtractionStatus,
    ResolutionMethod,
    ResolutionStatus,
    VerificationStatus,
)
from app.knowledge.repository import (
    ChunkRepository,
    ConflictRepository,
    DocumentRepository,
    EntityRepository,
    FactRepository,
)
from app.knowledge.schemas import (
    ConflictResolveRequest,
    ConflictResponse,
    DocumentDetailResponse,
    DocumentResponse,
    EntityDetailResponse,
    EntityResponse,
    FactResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Knowledge Browsing"])


# ============================================================================
# Entities Endpoints
# ============================================================================

@router.get("/entities", response_model=List[EntityResponse])
async def list_entities(
    query: Optional[str] = Query(None, description="Search term for entity canonical name or alias"),
    entity_type: Optional[EntityType] = Query(None, description="Filter by entity type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
) -> List[EntityResponse]:
    """List knowledge entities with alias mappings, supporting text search and type filtering."""
    entity_repo = EntityRepository(session)
    if query:
        entities = await entity_repo.search(query=query, limit=limit)
    else:
        entities = await entity_repo.get_all(skip=skip, limit=limit, entity_type=entity_type)
    return [EntityResponse.model_validate(e) for e in entities]


@router.get("/entities/{entity_id}", response_model=EntityDetailResponse)
async def get_entity_detail(
    entity_id: str,
    session: AsyncSession = Depends(get_db),
) -> EntityDetailResponse:
    """Retrieve full entity detail including linked facts and directional relationships."""
    entity_repo = EntityRepository(session)
    entity = await entity_repo.get(entity_id)
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found",
        )
    return EntityDetailResponse.model_validate(entity)


# ============================================================================
# Facts Endpoints
# ============================================================================

@router.get("/facts", response_model=List[FactResponse])
async def list_facts(
    entity_id: Optional[str] = Query(None, description="Filter by associated entity ID"),
    predicate: Optional[str] = Query(None, description="Filter by predicate name"),
    status: Optional[VerificationStatus] = Query(None, description="Filter by verification status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
) -> List[FactResponse]:
    """List extracted facts with optional filtering by entity, predicate, or verification status."""
    fact_repo = FactRepository(session)
    facts = await fact_repo.get_all(
        skip=skip,
        limit=limit,
        entity_id=entity_id,
        predicate=predicate,
        status=status,
    )
    return [FactResponse.model_validate(f) for f in facts]


@router.get("/facts/{fact_id}", response_model=FactResponse)
async def get_fact_detail(
    fact_id: str,
    session: AsyncSession = Depends(get_db),
) -> FactResponse:
    """Retrieve fact details including grounding evidence citations and conflicts."""
    fact_repo = FactRepository(session)
    fact = await fact_repo.get(fact_id)
    if not fact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fact '{fact_id}' not found",
        )
    return FactResponse.model_validate(fact)


# ============================================================================
# Conflicts Endpoints
# ============================================================================

@router.get("/conflicts", response_model=List[ConflictResponse])
async def list_conflicts(
    status: Optional[ResolutionStatus] = Query(None, description="Filter by resolution status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
) -> List[ConflictResponse]:
    """List all detected engineering conflicts across facts and revisions."""
    conflict_repo = ConflictRepository(session)
    conflicts = await conflict_repo.get_all(skip=skip, limit=limit, status=status)
    return [ConflictResponse.model_validate(c) for c in conflicts]


@router.get("/conflicts/{conflict_id}", response_model=ConflictResponse)
async def get_conflict_detail(
    conflict_id: str,
    session: AsyncSession = Depends(get_db),
) -> ConflictResponse:
    """Fetch details of a specific conflict and its involved facts."""
    conflict_repo = ConflictRepository(session)
    conflict = await conflict_repo.get(conflict_id)
    if not conflict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conflict '{conflict_id}' not found",
        )
    return ConflictResponse.model_validate(conflict)


@router.post("/conflicts/{conflict_id}/resolve", response_model=ConflictResponse)
async def resolve_conflict(
    conflict_id: str,
    req: ConflictResolveRequest,
    session: AsyncSession = Depends(get_db),
) -> ConflictResponse:
    """Document and execute resolution of a specification conflict."""
    conflict_repo = ConflictRepository(session)
    resolved = await conflict_repo.resolve(
        conflict_id=conflict_id,
        resolution_notes=req.resolution_notes,
        resolution_method=req.resolution_method,
        resolved_by=req.resolved_by,
        status=req.status,
    )
    if not resolved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conflict '{conflict_id}' not found",
        )
    return ConflictResponse.model_validate(resolved)


# ============================================================================
# Documents Endpoints
# ============================================================================

@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    status: Optional[ExtractionStatus] = Query(None, description="Filter by ingestion extraction status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
) -> List[DocumentResponse]:
    """List all ingested technical documents and their processing status."""
    doc_repo = DocumentRepository(session)
    docs = await doc_repo.get_all(skip=skip, limit=limit, status=status)
    return [DocumentResponse.model_validate(d) for d in docs]


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document_detail(
    document_id: str,
    session: AsyncSession = Depends(get_db),
) -> DocumentDetailResponse:
    """Retrieve document detail including all partitioned text chunks."""
    doc_repo = DocumentRepository(session)
    doc = await doc_repo.get(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found",
        )
    return DocumentDetailResponse.model_validate(doc)
