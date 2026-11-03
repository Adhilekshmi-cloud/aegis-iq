"""Tests for CRUD repositories in Aegis Knowledge System."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.models import (
    ConflictType,
    DocumentType,
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


@pytest.mark.asyncio
async def test_document_repository_crud(db_session: AsyncSession) -> None:
    """Test creating, retrieving, updating, and counting documents."""
    repo = DocumentRepository(db_session)

    doc = await repo.create(
        {
            "filename": "hydraulic_spec.pdf",
            "file_path": "/docs/hydraulic_spec.pdf",
            "doc_type": DocumentType.PDF,
            "revision": "Rev A",
        }
    )
    assert doc.document_id is not None
    assert doc.filename == "hydraulic_spec.pdf"

    # Fetch by ID
    fetched = await repo.get(doc.document_id)
    assert fetched is not None
    assert fetched.filename == "hydraulic_spec.pdf"

    # Update status
    updated = await repo.update_status(
        doc.document_id,
        status=ExtractionStatus.COMPLETED,
        chunk_count=12,
        fact_count=5,
    )
    assert updated.extraction_status == ExtractionStatus.COMPLETED
    assert updated.chunk_count == 12

    # Count
    cnt = await repo.count(ExtractionStatus.COMPLETED)
    assert cnt == 1


@pytest.mark.asyncio
async def test_entity_repository_crud(db_session: AsyncSession) -> None:
    """Test entity creation, alias resolution, and searching."""
    repo = EntityRepository(db_session)

    entity = await repo.create(
        {
            "canonical_name": "Hydraulic Pump HP-400",
            "entity_type": EntityType.COMPONENT,
            "description": "Main variable displacement pump",
            "aliases": ["HP-400", "Main Pump"],
        }
    )
    assert entity.entity_id is not None
    assert len(entity.aliases) == 2

    # Get by name
    found = await repo.get_by_name("hydraulic pump hp-400")
    assert found is not None
    assert found.entity_id == entity.entity_id

    # Search by alias
    results = await repo.search("Main Pump")
    assert len(results) >= 1
    assert results[0].canonical_name == "Hydraulic Pump HP-400"


@pytest.mark.asyncio
async def test_fact_and_conflict_repositories(db_session: AsyncSession) -> None:
    """Test fact creation and conflict linking."""
    entity_repo = EntityRepository(db_session)
    fact_repo = FactRepository(db_session)
    conflict_repo = ConflictRepository(db_session)
    doc_repo = DocumentRepository(db_session)

    doc = await doc_repo.create(
        {
            "filename": "pump_revA.txt",
            "file_path": "/docs/pump_revA.txt",
        }
    )

    entity = await entity_repo.create(
        {
            "canonical_name": "Relief Valve RV-1",
            "entity_type": EntityType.COMPONENT,
        }
    )

    fact1 = await fact_repo.create(
        {
            "entity_id": entity.entity_id,
            "predicate": "operating_pressure",
            "value": "350",
            "unit": "bar",
            "numeric_value": 350.0,
            "document_id": doc.document_id,
            "evidence_snippet": "operating pressure: 350 bar",
            "verification_status": VerificationStatus.VERIFIED,
        }
    )
    assert fact1.fact_id is not None
    assert len(fact1.evidence) == 1

    fact2 = await fact_repo.create(
        {
            "entity_id": entity.entity_id,
            "predicate": "operating_pressure",
            "value": "400",
            "unit": "bar",
            "numeric_value": 400.0,
            "verification_status": VerificationStatus.CONFLICTING,
        }
    )

    # Create conflict
    conflict = await conflict_repo.create(
        {
            "predicate": "operating_pressure",
            "description": "Pressure mismatch between Rev A (350 bar) and Rev B (400 bar)",
            "conflict_type": ConflictType.VALUE_MISMATCH,
            "status": ResolutionStatus.UNRESOLVED,
            "fact_ids": [fact1.fact_id, fact2.fact_id],
        }
    )
    assert conflict.conflict_id is not None
    assert len(conflict.facts) == 2

    # Resolve conflict
    resolved = await conflict_repo.resolve(
        conflict_id=conflict.conflict_id,
        resolution_notes="Adopted 400 bar from latest revision B",
        resolution_method=ResolutionMethod.NORMALIZED,
        resolved_by="lead_engineer",
    )
    assert resolved.status == ResolutionStatus.RESOLVED_BY_REVISION
    assert resolved.resolved_by == "lead_engineer"
