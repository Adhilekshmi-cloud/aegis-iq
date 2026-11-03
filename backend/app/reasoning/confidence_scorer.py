"""Confidence scorer - multi-factor scoring for answer quality assessment."""

import logging
from dataclasses import dataclass
from typing import Optional

from app.reasoning.evidence_assembler import AssembledEvidence, EvidenceItem

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceBreakdown:
    """Detailed breakdown of confidence score factors."""
    overall: float
    evidence_count_score: float
    trust_level_score: float
    agreement_score: float
    extraction_quality_score: float
    has_conflicts: bool
    explanation: str


TRUST_WEIGHTS = {
    "high": 1.0,
    "medium": 0.7,
    "low": 0.4,
    "unknown": 0.3,
}

EXTRACTION_WEIGHTS = {
    "rule": 1.0,
    "pattern": 0.95,
    "table": 0.9,
    "manual": 1.0,
    "llm": 0.7,
    "unknown": 0.5,
}


class ConfidenceScorer:
    """Scores answer confidence based on evidence quality and agreement."""

    def score(self, evidence: AssembledEvidence) -> ConfidenceBreakdown:
        """Calculate multi-factor confidence score.
        
        Factors:
        - Evidence count (more independent sources = higher)
        - Source trust levels (high-trust = higher)
        - Agreement between sources (consensus = higher)
        - Extraction quality (deterministic > LLM)
        
        Args:
            evidence: The assembled evidence to score.
            
        Returns:
            ConfidenceBreakdown with overall score and factor breakdown.
        """
        all_items = evidence.all_evidence
        
        if not all_items:
            return ConfidenceBreakdown(
                overall=0.0,
                evidence_count_score=0.0,
                trust_level_score=0.0,
                agreement_score=0.0,
                extraction_quality_score=0.0,
                has_conflicts=False,
                explanation="No evidence found for this question."
            )
        
        # Factor 1: Evidence count (0.0-1.0, logarithmic scaling)
        count = len(all_items)
        evidence_count_score = min(1.0, count / 5.0)  # 5+ items = max score
        
        # Factor 2: Trust level (weighted average of source trust)
        trust_scores = [TRUST_WEIGHTS.get(e.trust_level, 0.3) for e in all_items]
        trust_level_score = sum(trust_scores) / len(trust_scores) if trust_scores else 0.0
        
        # Factor 3: Agreement (do sources agree?)
        has_conflicts = len(evidence.conflicts) > 0
        if has_conflicts:
            # Penalize but don't zero out - conflicts are informative
            agreement_score = 0.4
        else:
            # Check value agreement for same predicates
            agreement_score = self._calculate_agreement(all_items)
        
        # Factor 4: Extraction quality
        extraction_scores = [
            EXTRACTION_WEIGHTS.get(e.extraction_method, 0.5) for e in all_items
        ]
        extraction_quality_score = (
            sum(extraction_scores) / len(extraction_scores) if extraction_scores else 0.0
        )
        
        # Weighted combination
        overall = (
            evidence_count_score * 0.2 +
            trust_level_score * 0.3 +
            agreement_score * 0.3 +
            extraction_quality_score * 0.2
        )
        
        # Build explanation
        explanation = self._build_explanation(
            overall, evidence_count_score, trust_level_score,
            agreement_score, extraction_quality_score, has_conflicts, count
        )
        
        logger.info(f"Confidence score: {overall:.2f} ({explanation})")
        
        return ConfidenceBreakdown(
            overall=round(overall, 3),
            evidence_count_score=round(evidence_count_score, 3),
            trust_level_score=round(trust_level_score, 3),
            agreement_score=round(agreement_score, 3),
            extraction_quality_score=round(extraction_quality_score, 3),
            has_conflicts=has_conflicts,
            explanation=explanation,
        )

    def _calculate_agreement(self, items: list[EvidenceItem]) -> float:
        """Calculate agreement score based on value consistency."""
        if len(items) <= 1:
            return 0.7  # Single source - moderate confidence
        
        # Group by predicate
        by_predicate: dict[str, list[str]] = {}
        for item in items:
            key = item.predicate.lower().strip()
            if key not in by_predicate:
                by_predicate[key] = []
            by_predicate[key].append(item.value)
        
        if not by_predicate:
            return 0.7
        
        # Check agreement within each predicate group
        agreements = []
        for predicate, values in by_predicate.items():
            if len(values) <= 1:
                agreements.append(0.8)
                continue
            
            # Check if all values match
            unique_values = set(v.strip().lower() for v in values if v)
            if len(unique_values) <= 1:
                agreements.append(1.0)  # Perfect agreement
            else:
                agreements.append(0.4)  # Disagreement
        
        return sum(agreements) / len(agreements) if agreements else 0.7

    def _build_explanation(
        self, overall: float, evidence_score: float, trust_score: float,
        agreement_score: float, extraction_score: float,
        has_conflicts: bool, count: int
    ) -> str:
        """Build human-readable confidence explanation."""
        parts = []
        
        if overall >= 0.8:
            parts.append("High confidence")
        elif overall >= 0.5:
            parts.append("Moderate confidence")
        else:
            parts.append("Low confidence")
        
        parts.append(f"based on {count} evidence item(s)")
        
        if has_conflicts:
            parts.append("with detected conflicts between sources")
        
        if trust_score >= 0.8:
            parts.append("from high-trust sources")
        elif trust_score < 0.5:
            parts.append("from low-trust sources")
        
        return "; ".join(parts) + "."
