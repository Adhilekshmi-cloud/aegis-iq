"""Answer generator - produces evidence-grounded answers with citations."""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from openai import AsyncOpenAI

from app.config import get_settings
from app.reasoning.evidence_assembler import AssembledEvidence, EvidenceItem, ConflictGroup
from app.reasoning.confidence_scorer import ConfidenceScorer, ConfidenceBreakdown

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """A source citation for a claim."""
    document: str
    page: Optional[int] = None
    section: Optional[str] = None
    source_text: Optional[str] = None
    trust_level: str = "unknown"


@dataclass
class AnswerClaim:
    """A single claim within an answer, with evidence."""
    claim: str
    evidence: list[Citation] = field(default_factory=list)


@dataclass 
class ConflictInfo:
    """Information about a detected conflict."""
    description: str
    values: list[dict] = field(default_factory=list)
    resolution_status: str = "unresolved"
    explanation: Optional[str] = None


@dataclass
class GeneratedAnswer:
    """A complete answer with evidence, conflicts, and confidence."""
    question: str
    answer: str
    claims: list[AnswerClaim] = field(default_factory=list)
    conflicts: list[ConflictInfo] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    confidence: float = 0.0
    confidence_breakdown: Optional[ConfidenceBreakdown] = None
    latency_seconds: float = 0.0
    source_count: int = 0
    method: str = "rule_based"  # rule_based or llm


class AnswerGenerator:
    """Generates evidence-grounded answers from assembled evidence."""

    def __init__(self):
        self.confidence_scorer = ConfidenceScorer()

    async def generate(self, evidence: AssembledEvidence) -> GeneratedAnswer:
        """Generate an answer from assembled evidence.
        
        Strategy:
        1. Try LLM-based generation if API key is available
        2. Fall back to rule-based answer assembly
        
        Args:
            evidence: The assembled evidence.
            
        Returns:
            GeneratedAnswer with citations, conflicts, and confidence.
        """
        start_time = time.time()
        
        # Score confidence first
        confidence = self.confidence_scorer.score(evidence)
        
        # Try LLM-based generation
        settings = get_settings()
        if settings.OPENAI_API_KEY:
            try:
                answer = await self._generate_with_llm(evidence, confidence)
                answer.latency_seconds = time.time() - start_time
                return answer
            except Exception as e:
                logger.warning(f"LLM generation failed, falling back to rules: {e}")
        
        # Fall back to rule-based
        answer = self._generate_rule_based(evidence, confidence)
        answer.latency_seconds = time.time() - start_time
        return answer

    def _generate_rule_based(
        self, evidence: AssembledEvidence, confidence: ConfidenceBreakdown
    ) -> GeneratedAnswer:
        """Generate answer using deterministic rules from structured facts."""
        query = evidence.query_analysis
        all_items = evidence.all_evidence
        
        answer = GeneratedAnswer(
            question=query.original_question,
            answer="",
            confidence=confidence.overall,
            confidence_breakdown=confidence,
            source_count=evidence.total_sources,
            method="rule_based",
        )
        
        # No evidence case
        if not all_items:
            answer.answer = (
                "The available documents do not contain sufficient information "
                "to answer this question."
            )
            answer.unknowns.append(
                f"No relevant evidence found for: {query.original_question}"
            )
            return answer
        
        # Build claims from evidence
        # Group by predicate
        by_predicate: dict[str, list[EvidenceItem]] = {}
        for item in all_items:
            key = item.predicate
            if key not in by_predicate:
                by_predicate[key] = []
            by_predicate[key].append(item)
        
        # Generate claims
        answer_parts = []
        for predicate, items in by_predicate.items():
            # Get unique values
            value_map: dict[str, list[EvidenceItem]] = {}
            for item in items:
                val_key = f"{item.value} {item.unit or ''}".strip()
                if val_key not in value_map:
                    value_map[val_key] = []
                value_map[val_key].append(item)
            
            if len(value_map) == 1:
                # Single agreed value
                val = list(value_map.keys())[0]
                supporting_items = list(value_map.values())[0]
                
                claim_text = f"The {predicate} is {val}."
                citations = [
                    Citation(
                        document=item.document_name,
                        page=item.page_number,
                        section=item.section,
                        source_text=item.source_text,
                        trust_level=item.trust_level,
                    )
                    for item in supporting_items
                ]
                answer.claims.append(AnswerClaim(claim=claim_text, evidence=citations))
                answer_parts.append(claim_text)
            else:
                # Multiple values - report conflict
                claim_parts = []
                all_citations = []
                for val, items_for_val in value_map.items():
                    sources = ", ".join(set(i.document_name for i in items_for_val))
                    revision_info = ""
                    for item in items_for_val:
                        if item.revision_scope:
                            revision_info = f" ({item.revision_scope})"
                            break
                    claim_parts.append(f"{val}{revision_info} per {sources}")
                    all_citations.extend([
                        Citation(
                            document=item.document_name,
                            page=item.page_number,
                            section=item.section,
                            source_text=item.source_text,
                            trust_level=item.trust_level,
                        )
                        for item in items_for_val
                    ])
                
                claim_text = (
                    f"The {predicate} has different values across documents: "
                    + "; ".join(claim_parts) + "."
                )
                answer.claims.append(AnswerClaim(claim=claim_text, evidence=all_citations))
                answer_parts.append(claim_text)
        
        # Build conflicts
        for cg in evidence.conflicts:
            values = []
            for item in cg.items:
                values.append({
                    "value": f"{item.value} {item.unit or ''}".strip(),
                    "source": item.document_name,
                    "revision": item.revision_scope,
                    "trust_level": item.trust_level,
                })
            answer.conflicts.append(ConflictInfo(
                description=f"Conflicting values for {cg.items[0].predicate if cg.items else 'unknown'}",
                values=values,
                resolution_status=cg.resolution_status,
                explanation=cg.explanation,
            ))
        
        # Build final answer text
        if answer.conflicts:
            answer_parts.insert(0, 
                "Note: The available documents contain conflicting information for this question."
            )
        
        answer.answer = " ".join(answer_parts) if answer_parts else (
            "The available documents do not contain sufficient information "
            "to answer this question."
        )
        
        return answer

    async def _generate_with_llm(
        self, evidence: AssembledEvidence, confidence: ConfidenceBreakdown
    ) -> GeneratedAnswer:
        """Generate answer using LLM grounded in retrieved evidence."""
        settings = get_settings()
        
        # Build context from evidence
        context_parts = []
        for i, item in enumerate(evidence.all_evidence[:20], 1):  # Limit context
            part = (
                f"[Evidence {i}] From: {item.document_name}"
                f" (Trust: {item.trust_level}"
                f"{', ' + item.revision_scope if item.revision_scope else ''})\n"
                f"  {item.predicate}: {item.value} {item.unit or ''}\n"
            )
            if item.source_text:
                part += f"  Source text: \"{item.source_text[:200]}\"\n"
            if item.page_number:
                part += f"  Page: {item.page_number}\n"
            context_parts.append(part)
        
        conflict_parts = []
        for cg in evidence.conflicts:
            vals = "; ".join(
                f"{item.value} {item.unit or ''} (from {item.document_name})"
                for item in cg.items
            )
            conflict_parts.append(f"CONFLICT: {vals} - Status: {cg.resolution_status}")
        
        system_prompt = (
            "You are a technical knowledge system for the Aegis Series-7 Hydraulic Control System. "
            "Answer questions using ONLY the provided evidence. Never fabricate specifications, "
            "page numbers, or citations. If evidence is insufficient, say so explicitly. "
            "If evidence conflicts, present ALL conflicting values with their sources. "
            "Always cite the source document for each claim."
        )
        
        user_prompt = (
            f"Question: {evidence.query_analysis.original_question}\n\n"
            f"Available Evidence:\n{''.join(context_parts)}\n"
        )
        if conflict_parts:
            user_prompt += f"\nDetected Conflicts:\n" + "\n".join(conflict_parts) + "\n"
        
        user_prompt += (
            "\nProvide a concise, accurate answer citing specific documents. "
            "If there are conflicts, explain them. If information is missing, state what is unknown."
        )
        
        client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=1000,
        )
        
        llm_answer = response.choices[0].message.content or ""
        
        # Build the GeneratedAnswer
        answer = GeneratedAnswer(
            question=evidence.query_analysis.original_question,
            answer=llm_answer,
            confidence=confidence.overall,
            confidence_breakdown=confidence,
            source_count=evidence.total_sources,
            method="llm",
        )
        
        # Add evidence as claims
        for item in evidence.all_evidence:
            answer.claims.append(AnswerClaim(
                claim=f"{item.predicate}: {item.value} {item.unit or ''}",
                evidence=[Citation(
                    document=item.document_name,
                    page=item.page_number,
                    section=item.section,
                    source_text=item.source_text,
                    trust_level=item.trust_level,
                )],
            ))
        
        # Add conflicts
        for cg in evidence.conflicts:
            values = []
            for item in cg.items:
                values.append({
                    "value": f"{item.value} {item.unit or ''}".strip(),
                    "source": item.document_name,
                    "revision": item.revision_scope,
                })
            answer.conflicts.append(ConflictInfo(
                description=f"Conflicting values detected",
                values=values,
                resolution_status=cg.resolution_status,
                explanation=cg.explanation,
            ))
        
        return answer
