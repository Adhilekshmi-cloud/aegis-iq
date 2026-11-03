"""Ingestion pipeline orchestrating document scanning, extraction, chunking, fact extraction, entity resolution, conflict detection, and database storage."""

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.entity_resolution.resolver import EntityResolver, default_resolver
from app.extraction.fact_extractor import ExtractedFactRecord, FactExtractor
from app.extraction.metadata_extractor import MetadataExtractor
from app.extraction.text_chunker import TextChunk, TextChunker
from app.ingestion.docx_extractor import DOCXExtractor
from app.ingestion.html_extractor import HTMLExtractor
from app.ingestion.json_extractor import JSONExtractor
from app.ingestion.ocr_extractor import OCRExtractor
from app.ingestion.pdf_extractor import PDFExtractor
from app.ingestion.png_extractor import PNGExtractor
from app.ingestion.pptx_extractor import PPTXExtractor
from app.ingestion.registry import ExtractionResult, ExtractorRegistry
from app.ingestion.xlsx_extractor import XLSXExtractor
from app.knowledge.models import (
    Conflict,
    ConflictType,
    Document,
    DocumentChunk,
    DocumentType,
    Entity,
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
)
from app.normalization.text_normalizer import normalize_text

logger = logging.getLogger(__name__)


@dataclass
class DocumentIngestionReport:
    """Report for an individual document's ingestion."""
    filename: str
    file_path: str
    status: str
    doc_type: str
    chunks_created: int = 0
    facts_extracted: int = 0
    conflicts_detected: int = 0
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)


@dataclass
class IngestionPipelineReport:
    """Consolidated summary report for the ingestion batch."""
    total_files_scanned: int = 0
    successful_ingestions: int = 0
    failed_ingestions: int = 0
    total_chunks: int = 0
    total_facts: int = 0
    total_conflicts: int = 0
    total_entities: int = 0
    duration_seconds: float = 0.0
    document_reports: List[DocumentIngestionReport] = field(default_factory=list)


def build_default_registry() -> ExtractorRegistry:
    """Instantiate and register all default format extractors."""
    reg = ExtractorRegistry()
    ocr = OCRExtractor()
    reg.register(PDFExtractor(ocr_extractor=ocr))
    reg.register(HTMLExtractor())
    reg.register(DOCXExtractor())
    reg.register(XLSXExtractor())
    reg.register(PPTXExtractor())
    reg.register(JSONExtractor())
    reg.register(PNGExtractor(ocr_extractor=ocr))
    return reg


def map_extension_to_doc_type(suffix: str, is_scanned: bool = False) -> DocumentType:
    """Map file extension to DocumentType enum."""
    ext = suffix.lower()
    if ext == ".pdf":
        return DocumentType.SCANNED_PDF if is_scanned else DocumentType.PDF
    elif ext in (".html", ".htm", ".xhtml"):
        return DocumentType.HTML
    elif ext in (".xlsx", ".xlsm", ".xltx"):
        return DocumentType.XLSX
    elif ext == ".docx":
        return DocumentType.DOCX
    elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
        return DocumentType.PNG
    elif ext == ".json":
        return DocumentType.JSON_DOC
    elif ext in (".pptx", ".pptm"):
        return DocumentType.PPTX
    elif ext in (".md", ".markdown"):
        return DocumentType.MARKDOWN
    return DocumentType.TEXT


class IngestionPipeline:
    """Main ingestion coordinator for the Aegis Knowledge System."""

    def __init__(
        self,
        registry: Optional[ExtractorRegistry] = None,
        resolver: Optional[EntityResolver] = None,
        chunker: Optional[TextChunker] = None,
        fact_extractor: Optional[FactExtractor] = None,
        metadata_extractor: Optional[MetadataExtractor] = None,
    ):
        """Initialize ingestion pipeline with components."""
        self.registry = registry or build_default_registry()
        self.resolver = resolver or default_resolver
        self.chunker = chunker or TextChunker()
        self.fact_extractor = fact_extractor or FactExtractor()
        self.metadata_extractor = metadata_extractor or MetadataExtractor()

    async def ingest_file(
        self,
        file_path: Path,
        session: AsyncSession,
    ) -> DocumentIngestionReport:
        """Process and ingest a single document file into the database.

        Steps:
        1. Select extractor from registry
        2. Extract raw text, tables, sections, metadata
        3. Normalize text
        4. Extract metadata & calculate trust level
        5. Partition into TextChunks
        6. Extract engineering facts
        7. Resolve entities
        8. Save Document, Chunks, Entities, Facts, Evidence
        9. Detect conflicts

        Args:
            file_path: Absolute or relative Path to target file.
            session: Active database AsyncSession.

        Returns:
            DocumentIngestionReport.
        """
        start_t = time.perf_counter()
        report = DocumentIngestionReport(
            filename=file_path.name,
            file_path=str(file_path),
            status="failed",
            doc_type="unknown",
        )

        try:
            logger.info("Starting ingestion of document: %s", file_path.name)
            extractor = self.registry.get_extractor(file_path)
            if not extractor:
                msg = f"No compatible extractor found for file type: {file_path.suffix}"
                logger.warning(msg)
                report.errors.append(msg)
                report.duration_seconds = round(time.perf_counter() - start_t, 2)
                return report

            # 1. Format-specific extraction
            extraction_res: ExtractionResult = await extractor.extract(file_path)
            if extraction_res.errors:
                report.errors.extend(extraction_res.errors)

            is_scanned = extraction_res.metadata.get("is_scanned", False)
            doc_type = map_extension_to_doc_type(file_path.suffix, is_scanned)
            report.doc_type = doc_type.value

            # 2. Text normalization
            normalized_content = normalize_text(extraction_res.text)

            # 3. Metadata extraction
            doc_meta = self.metadata_extractor.extract_metadata(
                file_path=file_path,
                doc_type=doc_type,
                text=normalized_content,
                extractor_meta=extraction_res.metadata,
            )

            # 4. Check if document already exists; if so, clear old records
            existing_doc_stmt = select(Document).where(Document.file_path == str(file_path))
            existing_doc_res = await session.execute(existing_doc_stmt)
            existing_doc = existing_doc_res.scalars().first()

            if existing_doc:
                logger.info("Re-ingesting existing document %s (id=%s)", file_path.name, existing_doc.document_id)
                await session.delete(existing_doc)
                await session.flush()

            # 5. Create Document record
            file_size = file_path.stat().st_size if file_path.exists() else 0
            document = Document(
                filename=file_path.name,
                file_path=str(file_path),
                doc_type=doc_type,
                doc_title=doc_meta.title,
                revision=doc_meta.revision,
                source_system=doc_meta.source_system,
                trust_level=doc_meta.trust_level,
                extraction_status=ExtractionStatus.PROCESSING,
                file_size_bytes=file_size,
                meta_info={
                    "author": doc_meta.author,
                    "date": doc_meta.date,
                    "ecn_references": doc_meta.ecn_references,
                    "page_count": extraction_res.page_count,
                    "extraction_method": extraction_res.extraction_method,
                    "confidence": extraction_res.confidence,
                },
            )
            session.add(document)
            await session.flush()

            # 6. Section-aware chunking
            chunks: List[TextChunk] = self.chunker.chunk_document(
                full_text=normalized_content,
                sections=extraction_res.sections,
                page_count=extraction_res.page_count,
                extra_meta={"document_id": document.document_id, "filename": file_path.name},
            )

            db_chunks: List[DocumentChunk] = []
            for c in chunks:
                db_chunk = DocumentChunk(
                    document_id=document.document_id,
                    chunk_index=c.chunk_index,
                    content=c.content,
                    page_number=c.page_number,
                    section_header=c.section_header,
                    token_count=c.token_count,
                    meta_info=c.metadata,
                )
                session.add(db_chunk)
                db_chunks.append(db_chunk)

            await session.flush()
            report.chunks_created = len(db_chunks)

            # 7. Fact extraction (Patterns, Tables, JSON, LLM)
            raw_facts: List[ExtractedFactRecord] = []

            # Patterns from chunks
            for c_idx, c in enumerate(chunks):
                chunk_facts = self.fact_extractor.extract_from_patterns(
                    chunk=c,
                    default_subject=doc_meta.title or "Aegis System",
                )
                # Link each fact to corresponding db_chunk
                for f in chunk_facts:
                    raw_facts.append(f)

            # Tables
            if extraction_res.tables:
                table_facts = self.fact_extractor.extract_from_tables(
                    tables=extraction_res.tables,
                    default_subject=doc_meta.title or "Aegis System",
                )
                raw_facts.extend(table_facts)

            # 8. Entity Resolution and DB Storage for Facts & Evidence
            db_facts: List[Fact] = []
            for rf in raw_facts:
                # Resolve entity
                entity, res_info = await self.resolver.resolve_or_create(
                    session=session,
                    raw_name=rf.subject,
                    entity_type=EntityType.COMPONENT,
                    system_context=doc_meta.source_system,
                )

                # Find best matching chunk for evidence
                matching_chunk_id = db_chunks[0].chunk_id if db_chunks else None
                for chk in db_chunks:
                    if rf.evidence_snippet and rf.evidence_snippet in chk.content:
                        matching_chunk_id = chk.chunk_id
                        break

                fact = Fact(
                    entity_id=entity.entity_id,
                    predicate=rf.predicate,
                    value=rf.value,
                    unit=rf.unit,
                    numeric_value=rf.numeric_value,
                    tolerance_min=rf.tolerance_min,
                    tolerance_max=rf.tolerance_max,
                    verification_status=VerificationStatus.VERIFIED if rf.confidence >= 0.8 else VerificationStatus.UNVERIFIED,
                    confidence_score=rf.confidence,
                    is_current=True,
                    meta_info={
                        "resolution_method": res_info.resolution_method.value,
                        "entity_needs_review": res_info.needs_review,
                        "raw_subject": rf.subject,
                    },
                )
                session.add(fact)
                await session.flush()
                db_facts.append(fact)

                # Create Evidence
                evidence = Evidence(
                    fact_id=fact.fact_id,
                    document_id=document.document_id,
                    chunk_id=matching_chunk_id,
                    snippet=rf.evidence_snippet or f"{rf.predicate}: {rf.value}",
                    page_number=rf.page_number,
                    confidence_score=rf.confidence,
                    extraction_method=rf.extraction_method,
                    meta_info={"section_header": rf.section_header},
                )
                session.add(evidence)

            await session.flush()
            report.facts_extracted = len(db_facts)

            # 9. Detect Conflicts for newly added facts
            conflicts_count = await self.detect_conflicts(session)
            report.conflicts_detected = conflicts_count

            # Finalize Document record
            document.chunk_count = len(db_chunks)
            document.fact_count = len(db_facts)
            document.extraction_status = ExtractionStatus.COMPLETED
            await session.flush()

            report.status = "completed"
            logger.info(
                "Successfully ingested %s: %d chunks, %d facts",
                file_path.name,
                report.chunks_created,
                report.facts_extracted,
            )

        except Exception as exc:
            logger.error("Error ingesting file %s: %s", file_path.name, exc, exc_info=True)
            report.status = "failed"
            report.errors.append(str(exc))

        report.duration_seconds = round(time.perf_counter() - start_t, 2)
        return report

    async def detect_conflicts(self, session: AsyncSession) -> int:
        """Detect and record value, version, or trust conflicts between facts.

        Groups all active facts by (entity_id, predicate.lower()).
        Where multiple facts differ in value or normalized unit:
        - Check if facts originate from differing document revisions
        - Check if facts originate from differing document trust levels
        - Record Conflict and link both facts via conflict_facts table

        Args:
            session: Active database AsyncSession.

        Returns:
            Number of newly recorded conflict records.
        """
        # Fetch all facts with their attached evidence and documents
        stmt = select(Fact).where(Fact.is_current == True)
        res = await session.execute(stmt)
        all_facts = res.scalars().all()

        # Group by (entity_id, predicate)
        grouped_facts: Dict[Tuple[str, str], List[Fact]] = {}
        for f in all_facts:
            key = (f.entity_id, f.predicate.strip().lower())
            if key not in grouped_facts:
                grouped_facts[key] = []
            grouped_facts[key].append(f)

        conflict_count = 0

        for (ent_id, pred_lower), facts_list in grouped_facts.items():
            if len(facts_list) < 2:
                continue

            # Compare pairs of facts
            unique_values = set(f.value.strip().lower() for f in facts_list)
            if len(unique_values) <= 1:
                continue

            # Differing values detected! Check if Conflict record already exists for this pair
            fact_ids = [f.fact_id for f in facts_list]

            # Determine conflict type and status
            # Look at evidence documents
            doc_ids = set()
            revisions = set()
            trust_levels = set()

            for f in facts_list:
                for ev in f.evidence:
                    if ev.document:
                        doc_ids.add(ev.document.document_id)
                        if ev.document.revision:
                            revisions.add(ev.document.revision)
                        if ev.document.trust_level:
                            trust_levels.add(ev.document.trust_level)

            conflict_type = ConflictType.VALUE_MISMATCH
            res_status = ResolutionStatus.UNRESOLVED

            if len(revisions) > 1:
                conflict_type = ConflictType.VERSION_DIFFERENCE
                res_status = ResolutionStatus.RESOLVED_BY_REVISION
            elif len(trust_levels) > 1:
                conflict_type = ConflictType.SOURCE_DISAGREEMENT
                res_status = ResolutionStatus.RESOLVED_BY_TRUST

            # Check if this conflict is already recorded in DB
            conflict_stmt = select(Conflict).where(
                Conflict.predicate == facts_list[0].predicate,
            )
            c_res = await session.execute(conflict_stmt)
            existing_conflicts = c_res.scalars().all()

            already_exists = False
            for ec in existing_conflicts:
                existing_fids = set(f.fact_id for f in ec.facts)
                if set(fact_ids).intersection(existing_fids):
                    already_exists = True
                    break

            if not already_exists:
                desc = (
                    f"Conflicting values detected for '{facts_list[0].predicate}': "
                    + ", ".join(f"'{f.value}'" for f in facts_list)
                )
                logger.warning("Detected %s: %s", conflict_type.value, desc)

                conflict = Conflict(
                    conflict_type=conflict_type,
                    predicate=facts_list[0].predicate,
                    description=desc,
                    status=res_status,
                    meta_info={
                        "entity_id": ent_id,
                        "values": [f.value for f in facts_list],
                        "revisions": list(revisions),
                        "trust_levels": [t.value for t in trust_levels],
                    },
                )
                conflict.facts = facts_list
                session.add(conflict)

                # Update verification status of conflicting facts
                for f in facts_list:
                    f.verification_status = VerificationStatus.CONFLICTING

                conflict_count += 1

        await session.flush()
        return conflict_count

    async def ingest_directory(
        self,
        directory_path: Path,
        session: AsyncSession,
        recursive: bool = True,
    ) -> IngestionPipelineReport:
        """Scan a directory for all documents and ingest each file.

        Args:
            directory_path: Root directory to scan.
            session: Active database AsyncSession.
            recursive: Whether to scan subdirectories.

        Returns:
            IngestionPipelineReport consolidating all ingestion results.
        """
        start_t = time.perf_counter()
        logger.info("Starting ingestion scan of directory: %s", directory_path)

        report = IngestionPipelineReport()

        if not directory_path.exists():
            logger.error("Ingestion directory does not exist: %s", directory_path)
            report.duration_seconds = round(time.perf_counter() - start_t, 2)
            return report

        # Discover all files matching supported extractor formats
        pattern = "**/*" if recursive else "*"
        all_candidates = [p for p in directory_path.glob(pattern) if p.is_file()]

        valid_files = [p for p in all_candidates if self.registry.get_extractor(p) is not None]
        report.total_files_scanned = len(valid_files)

        for f_path in valid_files:
            try:
                doc_rep = await self.ingest_file(f_path, session)
                report.document_reports.append(doc_rep)
                if doc_rep.status == "completed":
                    report.successful_ingestions += 1
                    report.total_chunks += doc_rep.chunks_created
                    report.total_facts += doc_rep.facts_extracted
                else:
                    report.failed_ingestions += 1
            except Exception as f_exc:
                logger.error("Unhandled error ingesting file %s: %s", f_path.name, f_exc)
                report.failed_ingestions += 1
                report.document_reports.append(
                    DocumentIngestionReport(
                        filename=f_path.name,
                        file_path=str(f_path),
                        status="failed",
                        doc_type="unknown",
                        errors=[str(f_exc)],
                    )
                )

        # Count total entities and conflicts in DB
        ent_res = await session.execute(select(Entity))
        report.total_entities = len(ent_res.scalars().all())

        conf_res = await session.execute(select(Conflict))
        report.total_conflicts = len(conf_res.scalars().all())

        report.duration_seconds = round(time.perf_counter() - start_t, 2)
        logger.info(
            "Ingestion batch completed: %d files (%d success, %d failed), %d chunks, %d facts, %d conflicts in %.2fs",
            report.total_files_scanned,
            report.successful_ingestions,
            report.failed_ingestions,
            report.total_chunks,
            report.total_facts,
            report.total_conflicts,
            report.duration_seconds,
        )
        return report
