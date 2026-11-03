"""Natural language evidence-grounded query engine for Aegis Knowledge System."""

import logging
import re
import time
from typing import List, Optional, Set

from app.config import settings

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.knowledge.models import Entity, Fact
from app.knowledge.repository import (
    ChunkRepository,
    ConflictRepository,
    DocumentRepository,
    EntityRepository,
    FactRepository,
)
from app.knowledge.schemas import (
    Claim,
    ConflictInfo,
    EvidenceItem,
    QueryRequest,
    QueryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/query", tags=["Query"])


def _llm_available() -> bool:
    """Return True if an OpenAI-compatible API key is configured."""
    return bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip())


async def _generate_llm_answer(
    question: str,
    claims: List,
    conflicts: List,
    evidence_items: List,
) -> Optional[str]:
    """
    Call OpenAI-compatible LLM to produce a natural-language answer grounded
    in the structured facts already retrieved.  Returns None on any error so
    the caller can fall back to the deterministic template.
    """
    if not _llm_available():
        return None
    try:
        from openai import AsyncOpenAI  # type: ignore
        client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        # Build a compact evidence block – no fabrication possible because
        # the LLM only sees pre-extracted, verified facts.
        facts_block = "\n".join(
            f"- {c.entity_name}: {c.predicate.replace('_', ' ')} = {c.value} {c.unit or ''} "
            f"[status: {c.status}, source: {c.source_doc or 'unknown'}]"
            for c in claims
        )
        conflict_block = "\n".join(
            f"- CONFLICT on {c.predicate}: {c.description}"
            for c in conflicts
        )
        snippet_block = "\n".join(
            f"- [{e.document_name or 'doc'} p.{e.page_number or '?'}]: {e.snippet[:120]}"
            for e in evidence_items[:4]
        )

        system_prompt = (
            "You are the Aegis Knowledge System — a precise technical assistant for the "
            "Aegis Series-7 Hydraulic Control System.\n"
            "Rules:\n"
            "1. Answer ONLY from the structured facts and evidence provided below.\n"
            "2. If facts conflict, clearly state all conflicting values and their sources.\n"
            "3. Never invent specifications, part numbers, or page references.\n"
            "4. If evidence is insufficient, say so explicitly.\n"
            "5. Be concise and technical."
        )

        user_prompt = (
            f"Question: {question}\n\n"
            f"Extracted Facts:\n{facts_block or 'None found.'}\n\n"
            f"Conflicts:\n{conflict_block or 'None.'}\n\n"
            f"Supporting Passages:\n{snippet_block or 'None.'}\n\n"
            "Answer (grounded in the above evidence only):"
        )

        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=512,
            temperature=0.1,  # Low temperature for factual consistency
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("LLM call failed, falling back to deterministic answer: %s", exc)
        return None

# Common engineering query keywords mapped to predicates
KEYWORD_TO_PREDICATE = {
    "pressure": "operating_pressure",
    "psi": "operating_pressure",
    "bar": "operating_pressure",
    "temp": "operating_temperature",
    "temperature": "operating_temperature",
    "flow": "flow_rate",
    "voltage": "rated_voltage",
    "volt": "rated_voltage",
    "weight": "weight",
    "mass": "weight",
    "torque": "torque",
    "tightening": "torque",
    "material": "material",
    "alloy": "material",
    "steel": "material",
    "tolerance": "tolerance",
    "clearance": "tolerance",
}


@router.post("", response_model=QueryResponse)
async def query_knowledge(
    req: QueryRequest,
    session: AsyncSession = Depends(get_db),
) -> QueryResponse:
    """
    Submit a natural language question and receive an evidence-grounded answer
    complete with claims, source citations, and conflict alerts.
    """
    start_time = time.time()
    logger.info("Processing query: '%s'", req.question)

    entity_repo = EntityRepository(session)
    fact_repo = FactRepository(session)
    chunk_repo = ChunkRepository(session)
    conflict_repo = ConflictRepository(session)
    doc_repo = DocumentRepository(session)

    claims: List[Claim] = []
    evidence_items: List[EvidenceItem] = []
    conflicts_info: List[ConflictInfo] = []

    # 1. Identify Target Entities
    matched_entities: List[Entity] = []
    if req.entity_filter:
        ent = await entity_repo.get_by_name(req.entity_filter)
        if ent:
            matched_entities.append(ent)
    else:
        # Search all entities against question keywords
        all_entities = await entity_repo.get_all(limit=100)
        q_lower = req.question.lower()
        for ent in all_entities:
            # Check canonical name or aliases
            if ent.canonical_name.lower() in q_lower:
                matched_entities.append(ent)
            else:
                for alias in ent.aliases:
                    if alias.alias_name.lower() in q_lower:
                        matched_entities.append(ent)
                        break

    # If no specific entity matched by exact substring, do fuzzy/text search
    if not matched_entities:
        words = [w for w in re.findall(r"\b[A-Za-z0-9_-]+\b", req.question) if len(w) > 3]
        for w in words[:3]:
            found = await entity_repo.search(w, limit=3)
            for f in found:
                if f not in matched_entities:
                    matched_entities.append(f)

    # 2. Identify Target Predicates from question
    target_predicates: Set[str] = set()
    q_words = req.question.lower().split()
    for word in q_words:
        clean_w = re.sub(r"[^\w]", "", word)
        if clean_w in KEYWORD_TO_PREDICATE:
            target_predicates.add(KEYWORD_TO_PREDICATE[clean_w])

    # 3. Retrieve Facts
    relevant_facts: List[Fact] = []
    if matched_entities:
        for ent in matched_entities:
            ent_facts = await fact_repo.get_by_entity(ent.entity_id)
            for f in ent_facts:
                if f.confidence_score < req.confidence_threshold:
                    continue
                if target_predicates and f.predicate not in target_predicates:
                    continue
                relevant_facts.append(f)
    elif target_predicates:
        for pred in target_predicates:
            p_facts = await fact_repo.get_by_predicate(pred)
            relevant_facts.extend(
                [f for f in p_facts if f.confidence_score >= req.confidence_threshold]
            )

    # 4. Process Facts into Claims & Evidence
    seen_fact_ids: Set[str] = set()
    entity_name_cache = {e.entity_id: e.canonical_name for e in matched_entities}

    for f in relevant_facts[: req.top_k]:
        if f.fact_id in seen_fact_ids:
            continue
        seen_fact_ids.add(f.fact_id)

        ent_name = entity_name_cache.get(f.entity_id)
        if not ent_name:
            ent_obj = await entity_repo.get(f.entity_id)
            ent_name = ent_obj.canonical_name if ent_obj else "Unknown Component"
            entity_name_cache[f.entity_id] = ent_name

        # Gather evidence snippets
        source_doc_name = None
        for ev in f.evidence:
            doc = await doc_repo.get(ev.document_id)
            doc_name = doc.filename if doc else "Document"
            if not source_doc_name:
                source_doc_name = doc_name

            evidence_items.append(
                EvidenceItem(
                    evidence_id=ev.evidence_id,
                    fact_id=f.fact_id,
                    document_name=doc_name,
                    snippet=ev.snippet,
                    page_number=ev.page_number,
                    confidence_score=ev.confidence_score,
                    extraction_method=ev.extraction_method.value,
                )
            )

        claims.append(
            Claim(
                claim_id=f.fact_id,
                entity_name=ent_name,
                predicate=f.predicate,
                value=f.value,
                unit=f.unit,
                status=f.verification_status.value,
                confidence=f.confidence_score,
                source_doc=source_doc_name,
            )
        )

        # 5. Check for Conflicts if requested
        if req.include_conflicts:
            conflicts = await conflict_repo.get_by_fact(f.fact_id)
            for c in conflicts:
                conflicting_vals = [cf.value for cf in c.facts]
                conflicts_info.append(
                    ConflictInfo(
                        conflict_id=c.conflict_id,
                        predicate=c.predicate,
                        description=c.description,
                        conflict_type=c.conflict_type.value,
                        status=c.status.value,
                        conflicting_values=conflicting_vals,
                        resolution_notes=c.resolution_notes,
                    )
                )

    # 6. Fallback Chunk Text Search if no facts directly retrieved
    if not claims:
        chunks = await chunk_repo.search_text(req.question, limit=req.top_k)
        for c in chunks:
            doc = await doc_repo.get(c.document_id)
            doc_name = doc.filename if doc else "Document"
            evidence_items.append(
                EvidenceItem(
                    fact_id=None,
                    document_name=doc_name,
                    snippet=c.content[:250] + "...",
                    page_number=c.page_number,
                    confidence_score=0.7,
                    extraction_method="text_search",
                )
            )

    # 7. Synthesize Authoritative Grounded Answer
    answer_parts: List[str] = []

    # --- Try LLM-enhanced answer first (only when key is configured) ---
    llm_answer = await _generate_llm_answer(
        question=req.question,
        claims=claims,
        conflicts=conflicts_info,
        evidence_items=evidence_items,
    )

    if llm_answer:
        answer_text = llm_answer
    elif claims:
        # Group claims by entity
        by_entity: dict = {}
        for cl in claims:
            by_entity.setdefault(cl.entity_name, []).append(cl)

        for ent_name, ent_claims in by_entity.items():
            specs_summary = ", ".join(
                f"{c.predicate.replace('_', ' ')}: {c.value} {c.unit or ''}".strip()
                for c in ent_claims
            )
            answer_parts.append(f"For {ent_name}, the documented specification is {specs_summary}.")

        if conflicts_info:
            c_desc = "; ".join(c.description for c in conflicts_info)
            answer_parts.append(
                f"\n[CRITICAL NOTE - Discrepancy Detected]: {c_desc}. "
                "Please verify revision levels before finalizing engineering design."
            )
    elif evidence_items:
        snippets = "\n".join(f"- {e.snippet}" for e in evidence_items[:2])
        answer_parts.append(
            f"Based on technical documentation search, the following relevant passages were found:\n{snippets}"
        )
    else:
        answer_parts.append(
            "No specific engineering facts or matching specifications were found in the Aegis Knowledge System "
            f"for '{req.question}'. Please ensure the relevant technical documents are ingested."
        )

    if not llm_answer:
        answer_text = "\n".join(answer_parts)
    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    overall_confidence = 0.95 if claims and not conflicts_info else (0.80 if claims else 0.50)

    return QueryResponse(
        question=req.question,
        answer=answer_text,
        confidence=overall_confidence,
        claims=claims,
        evidence=evidence_items,
        conflicts=conflicts_info,
        query_time_ms=elapsed_ms,
        status="success",
    )
