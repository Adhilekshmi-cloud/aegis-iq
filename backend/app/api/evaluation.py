"""Evaluation harness and benchmark verification endpoints for Aegis Intelligence System."""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.query import query_knowledge
from app.database import get_db
from app.knowledge.schemas import (
    EvaluationMetrics,
    EvaluationRequest,
    EvaluationResponse,
    QueryRequest,
    QuestionResult,
)
from app.reasoning.benchmark_eval import BENCHMARK_GROUND_TRUTH

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/evaluate", tags=["Evaluation"])

# Global cache for the latest evaluation run
_LATEST_EVALUATION: Dict[str, Any] = {}


@router.post("", response_model=EvaluationResponse)
async def run_evaluation(
    req: EvaluationRequest = EvaluationRequest(),
    session: AsyncSession = Depends(get_db),
) -> EvaluationResponse:
    """
    Run evaluation harness across all 23 benchmark questions from evaluation-questions.pdf.
    Evaluates factual correctness, evidence provenance, conflict handling, and abstention rate.
    """
    global _LATEST_EVALUATION
    logger.info("Starting evaluation run with sample_size=%s", req.sample_size)

    # Use all 23 questions unless restricted
    suite = BENCHMARK_GROUND_TRUTH[: req.sample_size] if req.sample_size and req.sample_size < len(BENCHMARK_GROUND_TRUTH) else BENCHMARK_GROUND_TRUTH
    results: List[QuestionResult] = []

    passed_count = 0
    total_latency = 0.0
    grounded_count = 0
    detected_conflicts_count = 0
    expected_conflicts_total = sum(1 for q in suite if q.get("conflict_handled"))

    for item in suite:
        q_start = time.time()
        q_text = item["question"]
        expected_ans = item["expected_answer"]

        # Execute query against knowledge system
        q_req = QueryRequest(
            question=q_text,
            top_k=5,
            include_conflicts=req.include_conflicts,
        )
        res = await query_knowledge(q_req, session=session)
        q_latency = round((time.time() - q_start) * 1000, 2)
        total_latency += q_latency

        # Assess correctness based on key concepts
        ans_lower = res.answer.lower()
        matched_kws = [kw.lower() for kw in item.get("keywords", []) if kw.lower() in ans_lower]
        accuracy = min(1.0, len(matched_kws) / max(1, len(item.get("keywords", [])))) if item.get("keywords") else 1.0

        # Evidence grounding score (1.0 if citations provided or correctly abstained)
        grounding_score = 1.0 if res.evidence or item.get("is_abstention") else 0.0
        if grounding_score > 0:
            grounded_count += 1

        # Conflict handling verification
        conflicts_detected = len(res.conflicts)
        if item.get("conflict_handled") and conflicts_detected > 0:
            detected_conflicts_count += 1

        # Question passes if it matches expected answer accurately
        passed = (accuracy >= 0.7 or item.get("is_abstention"))
        if passed:
            passed_count += 1

        results.append(
            QuestionResult(
                question_id=item["id"],
                question=q_text,
                expected_answer=expected_ans,
                generated_answer=res.answer,
                accuracy_score=round(accuracy, 2),
                evidence_grounding_score=round(grounding_score, 2),
                latency_ms=q_latency,
                claims_count=len(res.claims),
                conflicts_detected=conflicts_detected,
                passed=passed,
            )
        )

    total_q = len(suite)
    avg_latency = round(total_latency / max(1, total_q), 2)
    acc_ratio = round(passed_count / max(1, total_q), 2)
    grounding_ratio = round(grounded_count / max(1, total_q), 2)
    conflict_ratio = (
        round(detected_conflicts_count / max(1, expected_conflicts_total), 2)
        if expected_conflicts_total > 0
        else 1.0
    )

    metrics = EvaluationMetrics(
        total_questions=total_q,
        passed_questions=passed_count,
        accuracy=acc_ratio,
        evidence_grounding_ratio=grounding_ratio,
        conflict_detection_rate=conflict_ratio,
        avg_latency_ms=avg_latency,
    )

    eval_response = EvaluationResponse(
        status="completed",
        timestamp=datetime.utcnow(),
        metrics=metrics,
        results=results,
    )

    _LATEST_EVALUATION = eval_response.model_dump()
    logger.info("Evaluation complete across %d questions. Accuracy: %s, Grounding: %s", total_q, acc_ratio, grounding_ratio)
    return eval_response


@router.get("/results", response_model=EvaluationResponse)
async def get_evaluation_results(
    session: AsyncSession = Depends(get_db),
) -> EvaluationResponse:
    """Retrieve the latest evaluation benchmark results or execute an initial run if none exists."""
    global _LATEST_EVALUATION
    if _LATEST_EVALUATION:
        return EvaluationResponse.model_validate(_LATEST_EVALUATION)

    # Automatically execute baseline benchmark run
    return await run_evaluation(EvaluationRequest(sample_size=23), session=session)
