"""Evaluation metrics - calculations for answer quality assessment."""

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class QuestionMetrics:
    """Metrics for a single evaluation question."""
    question_id: str
    question: str
    expected_answer: str
    actual_answer: str
    answer_correct: bool = False
    answer_partial: bool = False
    evidence_precision: float = 0.0
    evidence_recall: float = 0.0
    citation_accurate: bool = False
    conflict_handled: bool = False
    abstention_correct: bool = False
    latency_seconds: float = 0.0
    requires_conflict_handling: bool = False
    expected_behavior: str = ""
    keyword_overlap: float = 0.0


@dataclass
class AggregateMetrics:
    """Aggregate metrics across all evaluation questions."""
    answer_accuracy: float = 0.0
    partial_accuracy: float = 0.0
    evidence_precision: float = 0.0
    evidence_recall: float = 0.0
    citation_accuracy: float = 0.0
    conflict_handling_accuracy: float = 0.0
    abstention_rate: float = 0.0
    avg_latency: float = 0.0
    total_questions: int = 0
    questions_answered: int = 0


def calculate_keyword_overlap(expected: str, actual: str) -> float:
    """Calculate keyword overlap between expected and actual answers.
    
    Args:
        expected: Expected answer text.
        actual: Actual answer text.
        
    Returns:
        Float between 0.0 and 1.0 representing keyword overlap.
    """
    if not expected or not actual:
        return 0.0
    
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "and", "or", "but", "if",
        "in", "on", "at", "to", "for", "of", "with", "by", "from", "that",
        "this", "it", "its", "not", "no", "all", "each", "every", "both",
    }
    
    def extract_keywords(text: str) -> set[str]:
        words = text.lower().split()
        return {w.strip(".,;:!?()[]{}\"'") for w in words if w.lower() not in stop_words and len(w) > 2}
    
    expected_keywords = extract_keywords(expected)
    actual_keywords = extract_keywords(actual)
    
    if not expected_keywords:
        return 0.0
    
    overlap = expected_keywords & actual_keywords
    return len(overlap) / len(expected_keywords)


def check_answer_correctness(
    expected: str, actual: str, threshold: float = 0.4
) -> tuple[bool, bool, float]:
    """Check if actual answer is correct based on keyword overlap.
    
    Args:
        expected: Expected answer text.
        actual: Actual answer text.
        threshold: Minimum overlap for partial correctness.
        
    Returns:
        Tuple of (exact_match, partial_match, overlap_score).
    """
    overlap = calculate_keyword_overlap(expected, actual)
    exact = overlap >= 0.7
    partial = overlap >= threshold
    return exact, partial, overlap


def check_conflict_handling(actual_answer: str, conflicts: list[dict]) -> bool:
    """Check if the answer properly handles conflicts.
    
    Args:
        actual_answer: The generated answer text.
        conflicts: List of conflict dicts from the answer.
        
    Returns:
        True if conflicts are properly surfaced.
    """
    conflict_indicators = [
        "conflict", "different values", "disagree", "contradicts",
        "revision", "ecn", "changed", "updated", "varies",
        "depending on", "rev a", "rev b",
    ]
    answer_lower = actual_answer.lower()
    has_indicator = any(ind in answer_lower for ind in conflict_indicators)
    has_conflicts_data = len(conflicts) > 0
    return has_indicator or has_conflicts_data


def check_abstention(actual_answer: str) -> bool:
    """Check if the answer appropriately abstains when evidence is insufficient.
    
    Args:
        actual_answer: The generated answer text.
        
    Returns:
        True if the answer indicates inability to determine.
    """
    abstention_indicators = [
        "cannot be determined", "not available", "no evidence",
        "insufficient", "not found", "unable to determine",
        "no document", "not specified", "not provided",
        "does not contain", "not mentioned",
    ]
    answer_lower = actual_answer.lower()
    return any(ind in answer_lower for ind in abstention_indicators)


def calculate_evidence_precision(
    cited_documents: list[str], relevant_documents: list[str]
) -> float:
    """Calculate evidence precision.
    
    Args:
        cited_documents: Documents cited in the answer.
        relevant_documents: Documents that should be cited.
        
    Returns:
        Precision score (0.0-1.0).
    """
    if not cited_documents:
        return 0.0
    
    relevant_set = set(d.lower() for d in relevant_documents)
    cited_set = set(d.lower() for d in cited_documents)
    
    if not cited_set:
        return 0.0
    
    correct = cited_set & relevant_set
    return len(correct) / len(cited_set)


def calculate_evidence_recall(
    cited_documents: list[str], relevant_documents: list[str]
) -> float:
    """Calculate evidence recall.
    
    Args:
        cited_documents: Documents cited in the answer.
        relevant_documents: Documents that should be cited.
        
    Returns:
        Recall score (0.0-1.0).
    """
    if not relevant_documents:
        return 1.0  # No relevant docs = perfect recall
    
    relevant_set = set(d.lower() for d in relevant_documents)
    cited_set = set(d.lower() for d in cited_documents)
    
    correct = cited_set & relevant_set
    return len(correct) / len(relevant_set)


def calculate_aggregate_metrics(
    question_metrics: list[QuestionMetrics],
) -> AggregateMetrics:
    """Calculate aggregate metrics from individual question metrics.
    
    Args:
        question_metrics: List of per-question metrics.
        
    Returns:
        AggregateMetrics with averaged scores.
    """
    total = len(question_metrics)
    if total == 0:
        return AggregateMetrics()
    
    correct = sum(1 for q in question_metrics if q.answer_correct)
    partial = sum(1 for q in question_metrics if q.answer_partial)
    
    conflict_questions = [q for q in question_metrics if q.requires_conflict_handling]
    conflict_correct = sum(1 for q in conflict_questions if q.conflict_handled)
    
    abstention_questions = [q for q in question_metrics if q.expected_behavior == "appropriate_abstention"]
    abstention_correct = sum(1 for q in abstention_questions if q.abstention_correct)
    
    return AggregateMetrics(
        answer_accuracy=correct / total if total else 0.0,
        partial_accuracy=partial / total if total else 0.0,
        evidence_precision=sum(q.evidence_precision for q in question_metrics) / total,
        evidence_recall=sum(q.evidence_recall for q in question_metrics) / total,
        citation_accuracy=sum(1 for q in question_metrics if q.citation_accurate) / total,
        conflict_handling_accuracy=(
            conflict_correct / len(conflict_questions) if conflict_questions else 1.0
        ),
        abstention_rate=(
            abstention_correct / len(abstention_questions) if abstention_questions else 1.0
        ),
        avg_latency=sum(q.latency_seconds for q in question_metrics) / total,
        total_questions=total,
        questions_answered=sum(1 for q in question_metrics if q.actual_answer),
    )
