"""Fuzzy string matching for entity resolution using RapidFuzz.

Implements token-based similarity calculations with confidence thresholds and
identifies ambiguous or low-confidence entity candidates for review.
"""

import logging
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

try:
    from rapidfuzz import fuzz, process
    _RAPIDFUZZ_AVAILABLE = True
except ImportError:
    _RAPIDFUZZ_AVAILABLE = False
    import difflib

logger = logging.getLogger(__name__)

DEFAULT_MATCH_THRESHOLD = 0.85
AMBIGUITY_THRESHOLD = 0.70


@dataclass
class FuzzyMatchResult:
    """Result of a fuzzy matching operation."""
    matched_term: str
    target_entity: str
    score: float
    is_ambiguous: bool = False
    needs_review: bool = False


def calculate_similarity(s1: str, s2: str) -> float:
    """Calculate token-aware similarity score between two strings, normalized to [0.0, 1.0].

    Uses rapidfuzz token_sort_ratio or token_set_ratio if available, with difflib fallback.

    Args:
        s1: First string.
        s2: Second string.

    Returns:
        Similarity score between 0.0 and 1.0.
    """
    if not s1 or not s2:
        return 0.0

    s1_clean = s1.strip().lower()
    s2_clean = s2.strip().lower()

    if s1_clean == s2_clean:
        return 1.0

    if _RAPIDFUZZ_AVAILABLE:
        # Use combination of token_sort_ratio and ratio for robust matching
        token_score = fuzz.token_sort_ratio(s1_clean, s2_clean) / 100.0
        ratio_score = fuzz.ratio(s1_clean, s2_clean) / 100.0
        return max(token_score, ratio_score)
    else:
        # Fallback to standard library difflib
        matcher = difflib.SequenceMatcher(None, s1_clean, s2_clean)
        return matcher.ratio()


def fuzzy_match(
    candidate: str,
    choices: Iterable[str],
    threshold: float = DEFAULT_MATCH_THRESHOLD,
    ambiguity_threshold: float = AMBIGUITY_THRESHOLD,
) -> Optional[FuzzyMatchResult]:
    """Find the best matching choice for a given candidate string above threshold.

    Args:
        candidate: Candidate string to match.
        choices: Iterable of target choices.
        threshold: Minimum similarity score to be considered a match (default 0.85).
        ambiguity_threshold: Lower threshold below which candidates are marked for review.

    Returns:
        FuzzyMatchResult if match found, or None if below ambiguity threshold.
    """
    if not candidate:
        return None

    choice_list = list(choices)
    if not choice_list:
        return None

    best_choice: Optional[str] = None
    best_score: float = -1.0
    second_best_score: float = -1.0

    for choice in choice_list:
        score = calculate_similarity(candidate, choice)
        if score > best_score:
            second_best_score = best_score
            best_score = score
            best_choice = choice
        elif score > second_best_score:
            second_best_score = score

    if best_choice is None:
        return None

    # Check if multiple choices have very close scores (ambiguous)
    is_ambiguous = (
        second_best_score > 0.0
        and (best_score - second_best_score) < 0.05
        and best_score >= ambiguity_threshold
    )
    needs_review = (best_score < threshold) or is_ambiguous

    if best_score >= ambiguity_threshold:
        return FuzzyMatchResult(
            matched_term=candidate,
            target_entity=best_choice,
            score=round(best_score, 4),
            is_ambiguous=is_ambiguous,
            needs_review=needs_review,
        )

    return None


def match_against_dictionary(
    candidate: str,
    alias_dict: dict[str, str],
    threshold: float = DEFAULT_MATCH_THRESHOLD,
) -> Optional[FuzzyMatchResult]:
    """Match a candidate string against a dict of {alias_or_name: canonical_id}.

    Args:
        candidate: Input candidate string.
        alias_dict: Mapping of term to canonical entity ID.
        threshold: Minimum match score.

    Returns:
        FuzzyMatchResult with target_entity set to canonical entity ID.
    """
    terms = list(alias_dict.keys())
    res = fuzzy_match(candidate, terms, threshold=threshold)
    if res:
        canonical_id = alias_dict[res.target_entity]
        return FuzzyMatchResult(
            matched_term=candidate,
            target_entity=canonical_id,
            score=res.score,
            is_ambiguous=res.is_ambiguous,
            needs_review=res.needs_review,
        )
    return None
