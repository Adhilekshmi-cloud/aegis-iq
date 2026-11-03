"""Ingestion endpoints and document processing pipeline for Aegis Knowledge System."""

import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.knowledge.models import (
    ConflictType,
    DocumentType,
    EntityType,
    ExtractionMethod,
    ExtractionStatus,
    ResolutionStatus,
    TrustLevel,
    VerificationStatus,
    generate_uuid,
)
from app.knowledge.repository import (
    ChunkRepository,
    ConflictRepository,
    DocumentRepository,
    EntityRepository,
    FactRepository,
)
from app.knowledge.schemas import (
    DocumentChunkCreate,
    DocumentCreate,
    DocumentResponse,
    FactCreate,
    IngestionReportResponse,
    IngestionStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingest", tags=["Ingestion"])

# Global tracker for ingestion jobs
_INGESTION_STATE: Dict[str, Any] = {
    "is_ingesting": False,
    "last_job_id": None,
    "last_ingested_at": None,
    "last_report": None,
}

# Regex patterns for common engineering parameters
SPEC_PATTERNS = [
    # Pressure (e.g., "max pressure: 350 bar", "operating pressure = 5000 psi")
    (
        r"(?:max(?:imum)?|operating|rated|working|test)?\s*pressure\s*[:=]\s*([\d\.]+)\s*(psi|bar|mpa|kpa)",
        "operating_pressure",
        "pressure",
    ),
    # Temperature (e.g., "temperature: -40 to 125 C", "max temp: 200 °C")
    (
        r"(?:operating|ambient|fluid|max(?:imum)?)?\s*temp(?:erature)?\s*[:=]\s*([-\d\.]+(?:\s*(?:to|-)\s*[\d\.]+)?)\s*(?:°\s*)?(c|f|k)\b",
        "operating_temperature",
        "temperature",
    ),
    # Flow rate (e.g., "flow rate: 45 L/min", "rated flow: 12 gpm")
    (
        r"(?:rated|max(?:imum)?|nominal)?\s*flow(?:\s*rate)?\s*[:=]\s*([\d\.]+)\s*(l/min|gpm|m3/h|lpm)",
        "flow_rate",
        "flow",
    ),
    # Voltage (e.g., "supply voltage: 24 VDC", "voltage: 120 VAC")
    (
        r"(?:supply|input|rated)?\s*voltage\s*[:=]\s*([\d\.]+)\s*(vdc|vac|v)\b",
        "rated_voltage",
        "electrical",
    ),
    # Weight / Mass (e.g., "weight: 4.5 kg", "dry weight: 12 lbs")
    (
        r"(?:dry\s*)?weight\s*[:=]\s*([\d\.]+)\s*(kg|g|lbs|lb|ton)",
        "weight",
        "mass",
    ),
    # Torque (e.g., "tightening torque: 45 Nm", "torque: 35 ft-lbs")
    (
        r"(?:tightening|rated|max)?\s*torque\s*[:=]\s*([\d\.]+)\s*(nm|ft-lb|in-lb)",
        "torque",
        "mechanical",
    ),
    # Material (e.g., "material: 316L Stainless Steel", "housing material: Aluminum 6061-T6")
    (
        r"(?:housing\s*|seal\s*|body\s*)?material\s*[:=]\s*([A-Za-z0-9\-\s/]{3,35})(?:\.|\n|$)",
        "material",
        "material",
    ),
    # Tolerance / Clearance (e.g., "clearance: 0.05 mm", "tolerance: +/- 0.02 mm")
    (
        r"(?:clearance|tolerance)\s*[:=]\s*(?:(?:\+/-|\±)\s*)?([\d\.]+)\s*(mm|um|in|thou)",
        "tolerance",
        "dimension",
    ),
]


def detect_document_type(filename: str) -> DocumentType:
    """Infer document type enum from file extension."""
    ext = Path(filename).suffix.lower()
    mapping = {
        ".pdf": DocumentType.PDF,
        ".html": DocumentType.HTML,
        ".htm": DocumentType.HTML,
        ".xlsx": DocumentType.XLSX,
        ".xls": DocumentType.XLSX,
        ".docx": DocumentType.DOCX,
        ".png": DocumentType.PNG,
        ".jpg": DocumentType.PNG,
        ".jpeg": DocumentType.PNG,
        ".json": DocumentType.JSON_DOC,
        ".pptx": DocumentType.PPTX,
        ".md": DocumentType.MARKDOWN,
        ".txt": DocumentType.TEXT,
    }
    return mapping.get(ext, DocumentType.TEXT)


def extract_text_from_file(file_path: str) -> str:
    """Extract plain text from various file formats."""
    ext = Path(file_path).suffix.lower()
    try:
        if ext == ".pdf":
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                text_parts = [page.get_text() for page in doc]
                return "\n\n".join(text_parts)
            except ImportError:
                logger.warning("PyMuPDF not installed, reading PDF as binary fallback.")
                return f"[PDF document at {file_path}]"
        elif ext in [".md", ".txt", ".json", ".html", ".htm"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif ext == ".docx":
            try:
                import docx
                doc = docx.Document(file_path)
                return "\n".join([p.text for p in doc.paragraphs if p.text])
            except Exception as e:
                logger.warning("Could not parse docx %s: %s", file_path, e)
                return f"[DOCX document at {file_path}]"
        else:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
    except Exception as exc:
        logger.error("Error reading file %s: %s", file_path, exc)
        return ""


def chunk_document_text(text: str, chunk_size: int = 600, overlap: int = 100) -> List[Dict[str, Any]]:
    """Split text into manageable chunks preserving paragraph structure."""
    if not text.strip():
        return []

    paragraphs = text.split("\n\n")
    chunks: List[Dict[str, Any]] = []
    current_content = ""
    current_header = None
    chunk_index = 0

    for para in paragraphs:
        cleaned = para.strip()
        if not cleaned:
            continue

        # Check if line looks like a header (e.g., "## Specification" or "1.0 Hydraulic System")
        if re.match(r"^(?:#{1,4}\s+|[0-9]+\.[0-9]*\s+[A-Z])", cleaned):
            current_header = cleaned.split("\n")[0][:80]

        if len(current_content) + len(cleaned) <= chunk_size:
            current_content += ("\n\n" + cleaned if current_content else cleaned)
        else:
            if current_content:
                chunks.append({
                    "chunk_index": chunk_index,
                    "content": current_content,
                    "section_header": current_header,
                    "token_count": len(current_content.split()),
                })
                chunk_index += 1
                # Start new chunk with overlap
                current_content = current_content[-overlap:] + "\n" + cleaned
            else:
                current_content = cleaned

    if current_content:
        chunks.append({
            "chunk_index": chunk_index,
            "content": current_content,
            "section_header": current_header,
            "token_count": len(current_content.split()),
        })

    return chunks


async def process_document_pipeline(
    file_path: str,
    filename: str,
    session: AsyncSession,
    revision: Optional[str] = None,
    source_system: Optional[str] = "Manual Ingest",
) -> Tuple[Optional[DocumentResponse], int, int, int]:
    """
    Core pipeline to ingest one document:
    1. Register document in database
    2. Extract text & create chunks
    3. Extract entities & facts using pattern rules
    4. Detect conflicts with existing knowledge
    """
    doc_repo = DocumentRepository(session)
    chunk_repo = ChunkRepository(session)
    entity_repo = EntityRepository(session)
    fact_repo = FactRepository(session)
    conflict_repo = ConflictRepository(session)

    # Check if already exists
    existing = await doc_repo.get_by_path(file_path)
    if existing:
        doc_id = existing.document_id
        await doc_repo.update_status(doc_id, ExtractionStatus.PROCESSING)
        document = existing
    else:
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        doc_type = detect_document_type(filename)
        doc_in = DocumentCreate(
            filename=filename,
            file_path=file_path,
            doc_type=doc_type,
            doc_title=Path(filename).stem.replace("_", " ").title(),
            revision=revision or "Rev A",
            source_system=source_system,
            trust_level=TrustLevel.HIGH if "spec" in filename.lower() else TrustLevel.MEDIUM,
            file_size_bytes=file_size,
        )
        document = await doc_repo.create(doc_in)
        doc_id = document.document_id

    # Extract text content
    text = extract_text_from_file(file_path)
    if not text.strip():
        await doc_repo.update_status(
            doc_id, ExtractionStatus.FAILED, error_message="Empty file content"
        )
        return None, 0, 0, 0

    # Create chunks
    chunk_data_list = chunk_document_text(text)
    saved_chunks = []
    for c_data in chunk_data_list:
        chunk = await chunk_repo.create(
            DocumentChunkCreate(
                document_id=doc_id,
                chunk_index=c_data["chunk_index"],
                content=c_data["content"],
                section_header=c_data["section_header"],
                token_count=c_data["token_count"],
            )
        )
        saved_chunks.append(chunk)

    # Extract or infer primary entity from document title or headers
    stem_name = Path(filename).stem.replace("_", " ").title()
    primary_entity = await entity_repo.get_by_name(stem_name)
    if not primary_entity:
        primary_entity = await entity_repo.create(
            {
                "canonical_name": stem_name,
                "entity_type": EntityType.COMPONENT if "pump" in stem_name.lower() or "valve" in stem_name.lower() else EntityType.SYSTEM,
                "description": f"Extracted from document {filename}",
                "system_context": "Mechanical/Hydraulics",
            }
        )

    facts_count = 0
    conflicts_count = 0

    # Extract facts from each chunk
    for chunk in saved_chunks:
        chunk_text = chunk.content
        for pattern, predicate, category in SPEC_PATTERNS:
            matches = re.finditer(pattern, chunk_text, re.IGNORECASE)
            for match in matches:
                val = match.group(1).strip()
                unit = match.group(2).strip() if len(match.groups()) >= 2 and match.group(2) else None
                snippet = chunk_text[max(0, match.start() - 40) : min(len(chunk_text), match.end() + 40)].strip()

                # Parse float value if available
                num_val = None
                try:
                    num_val = float(val)
                except ValueError:
                    pass

                # Check if this fact already exists or conflicts
                existing_facts = await fact_repo.get_by_predicate(predicate, primary_entity.entity_id)
                fact_obj = None

                # Check for conflict: same predicate and entity, but differing value
                conflict_found = False
                for ef in existing_facts:
                    if ef.value.lower() != val.lower():
                        # Conflict detected!
                        desc = (
                            f"Mismatch on {predicate} for {primary_entity.canonical_name}: "
                            f"Existing='{ef.value} {ef.unit or ''}' vs Document='{val} {unit or ''}'"
                        )
                        # Create new fact record first
                        new_fact = await fact_repo.create(
                            FactCreate(
                                entity_id=primary_entity.entity_id,
                                predicate=predicate,
                                value=val,
                                unit=unit,
                                numeric_value=num_val,
                                verification_status=VerificationStatus.CONFLICTING,
                                confidence_score=0.85,
                                evidence_snippet=snippet,
                                document_id=doc_id,
                                chunk_id=chunk.chunk_id,
                                extraction_method=ExtractionMethod.PATTERN,
                            )
                        )
                        facts_count += 1

                        # Mark existing fact as conflicting
                        await fact_repo.update(
                            ef.fact_id, {"verification_status": VerificationStatus.CONFLICTING}
                        )

                        # Record conflict
                        await conflict_repo.create(
                            {
                                "predicate": predicate,
                                "description": desc,
                                "conflict_type": ConflictType.VALUE_MISMATCH,
                                "status": ResolutionStatus.UNRESOLVED,
                                "fact_ids": [ef.fact_id, new_fact.fact_id],
                                "meta_info": {
                                    "entity_name": primary_entity.canonical_name,
                                    "doc_filename": filename,
                                    "revision": revision,
                                },
                            }
                        )
                        conflicts_count += 1
                        conflict_found = True
                        break

                if not conflict_found and not any(ef.value.lower() == val.lower() for ef in existing_facts):
                    fact_obj = await fact_repo.create(
                        FactCreate(
                            entity_id=primary_entity.entity_id,
                            predicate=predicate,
                            value=val,
                            unit=unit,
                            numeric_value=num_val,
                            verification_status=VerificationStatus.VERIFIED,
                            confidence_score=0.95,
                            evidence_snippet=snippet,
                            document_id=doc_id,
                            chunk_id=chunk.chunk_id,
                            extraction_method=ExtractionMethod.PATTERN,
                        )
                    )
                    facts_count += 1

    # Update document status
    updated_doc = await doc_repo.update_status(
        doc_id,
        ExtractionStatus.COMPLETED,
        chunk_count=len(saved_chunks),
        fact_count=facts_count,
    )

    doc_response = DocumentResponse.model_validate(updated_doc) if updated_doc else None
    return doc_response, len(saved_chunks), facts_count, conflicts_count


def _ensure_sample_dataset_if_empty(data_dir: Path) -> List[str]:
    """Create sample engineering documents if data directory is empty so ingestion works out of the box."""
    data_dir.mkdir(parents=True, exist_ok=True)
    existing_files = list(data_dir.glob("*.*"))
    if existing_files:
        return [str(p) for p in existing_files]

    # Populate standard Aegis sample engineering documents
    sample_docs = [
        (
            "hydraulic_power_unit_spec.txt",
            """# Aegis Model HPU-5000 Hydraulic Power Unit
## System Overview
The Aegis HPU-5000 is a heavy-duty hydraulic power unit engineered for industrial automation.

## Technical Specifications (Revision A)
- System: Main Hydraulic Power Unit
- Operating Pressure: 350 bar
- Flow Rate: 45 L/min
- Ambient Temperature: -20 to 60 C
- Fluid Temp: -40 to 125 C
- Supply Voltage: 24 VDC
- Dry Weight: 185 kg
- Housing Material: Stainless Steel 316L
- Tightening Torque: 75 Nm
- Tolerance: +/- 0.05 mm
""",
        ),
        (
            "hydraulic_power_unit_revB.txt",
            """# Aegis Model HPU-5000 Hydraulic Power Unit
## Engineering Change Notice (Revision B)
Updated specifications following thermal stress testing.

## Modified Parameters
- System: Main Hydraulic Power Unit
- Operating Pressure: 380 bar
- Flow Rate: 50 L/min
- Supply Voltage: 24 VDC
- Housing Material: Aluminum 6061-T6
- Tightening Torque: 80 Nm
- Tolerance: +/- 0.02 mm
""",
        ),
        (
            "pressure_relief_valve_manual.txt",
            """# Model PRV-200 Pressure Relief Valve
## Component Description
Inline cartridge relief valve designed for high-pressure circuit protection.

## Specifications
- Component: Pressure Relief Valve PRV-200
- Operating Pressure: 420 bar
- Flow Rate: 120 L/min
- Body Material: Hardened Alloy Steel
- Tightening Torque: 45 Nm
- Ambient Temperature: -30 to 90 C
""",
        ),
    ]

    created_paths = []
    for fname, content in sample_docs:
        fpath = data_dir / fname
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        created_paths.append(str(fpath))
    logger.info("Generated %d sample documents in %s", len(created_paths), data_dir)
    return created_paths


@router.post("", response_model=IngestionReportResponse)
async def trigger_ingestion(
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
) -> IngestionReportResponse:
    """
    Trigger document ingestion scanning from the configured DATA_DIR.
    Extracts chunks, entities, facts, and identifies conflicts.
    """
    start_time = time.time()
    job_id = generate_uuid()
    _INGESTION_STATE["is_ingesting"] = True
    _INGESTION_STATE["last_job_id"] = job_id

    data_dir_path = Path(settings.DATA_DIR)
    file_paths = _ensure_sample_dataset_if_empty(data_dir_path)

    total_chunks = 0
    total_facts = 0
    total_conflicts = 0
    processed_count = 0
    failed_count = 0
    details: List[Dict[str, Any]] = []
    errors: List[str] = []

    for fpath in file_paths:
        fname = Path(fpath).name
        try:
            doc_res, c_cnt, f_cnt, conf_cnt = await process_document_pipeline(
                file_path=str(fpath),
                filename=fname,
                session=session,
            )
            processed_count += 1
            total_chunks += c_cnt
            total_facts += f_cnt
            total_conflicts += conf_cnt
            details.append({
                "filename": fname,
                "status": "success",
                "chunks": c_cnt,
                "facts": f_cnt,
                "conflicts": conf_cnt,
            })
        except Exception as exc:
            failed_count += 1
            err_msg = f"Failed processing {fname}: {str(exc)}"
            logger.exception(err_msg)
            errors.append(err_msg)
            details.append({"filename": fname, "status": "failed", "error": str(exc)})

    elapsed = round(time.time() - start_time, 2)
    _INGESTION_STATE["is_ingesting"] = False
    _INGESTION_STATE["last_ingested_at"] = datetime.utcnow()

    report = IngestionReportResponse(
        job_id=job_id,
        status="completed" if failed_count == 0 else "partial",
        documents_processed=processed_count,
        documents_failed=failed_count,
        total_chunks_created=total_chunks,
        total_facts_extracted=total_facts,
        total_conflicts_identified=total_conflicts,
        processing_time_seconds=elapsed,
        details=details,
        errors=errors,
    )
    _INGESTION_STATE["last_report"] = report.model_dump()
    return report


@router.get("/status", response_model=IngestionStatusResponse)
async def get_ingestion_status(
    session: AsyncSession = Depends(get_db),
) -> IngestionStatusResponse:
    """Get the current ingestion status and summary statistics across all knowledge entities."""
    doc_repo = DocumentRepository(session)
    chunk_repo = ChunkRepository(session)
    fact_repo = FactRepository(session)
    conflict_repo = ConflictRepository(session)

    total_docs = await doc_repo.count()
    completed_docs = await doc_repo.count(ExtractionStatus.COMPLETED)
    failed_docs = await doc_repo.count(ExtractionStatus.FAILED)
    total_chunks = await chunk_repo.count()
    total_facts = await fact_repo.count()
    total_conflicts = await conflict_repo.count()

    system_status = "idle"
    if _INGESTION_STATE["is_ingesting"]:
        system_status = "processing"
    elif failed_docs > 0:
        system_status = "has_errors"
    elif total_docs > 0:
        system_status = "ready"

    return IngestionStatusResponse(
        status=system_status,
        total_documents=total_docs,
        completed_documents=completed_docs,
        failed_documents=failed_docs,
        total_chunks=total_chunks,
        total_facts=total_facts,
        total_conflicts=total_conflicts,
        active_jobs=1 if _INGESTION_STATE["is_ingesting"] else 0,
        last_ingested_at=_INGESTION_STATE.get("last_ingested_at"),
    )


@router.post("/document", response_model=DocumentResponse)
async def ingest_single_document(
    file: UploadFile = File(...),
    revision: Optional[str] = "Rev A",
    source_system: Optional[str] = "Manual Upload",
    session: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Upload and ingest a single document directly."""
    upload_dir = Path("./uploaded_docs")
    upload_dir.mkdir(parents=True, exist_ok=True)
    target_path = upload_dir / file.filename

    # Save uploaded file
    try:
        content = await file.read()
        with open(target_path, "wb") as f:
            f.write(content)
    except Exception as exc:
        logger.error("Failed saving uploaded file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(exc)}",
        )

    doc_response, _, _, _ = await process_document_pipeline(
        file_path=str(target_path),
        filename=file.filename,
        session=session,
        revision=revision,
        source_system=source_system,
    )

    if not doc_response:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to extract or parse document content.",
        )

    return doc_response
