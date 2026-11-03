"""Evaluation harness and benchmark verification endpoints for Aegis Knowledge System."""

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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/evaluate", tags=["Evaluation"])

# Global cache for the latest evaluation run
_LATEST_EVALUATION: Dict[str, Any] = {}

# Standard benchmark evaluation suite for technical engineering systems
BENCHMARK_QUESTIONS = [
    {
        "id": "q1",
        "question": "What is the operating pressure of the HPU-5000 Hydraulic Power Unit?",
        "expected_answer": "350 bar",
        "expected_conflict": True,
        "keywords": ["pressure", "350", "380", "bar"],
    },
    {
        "id": "q2",
        "question": "What is the flow rate of the Model PRV-200 Pressure Relief Valve?",
        "expected_answer": "120 L/min",
        "expected_conflict": False,
        "keywords": ["flow", "120", "l/min"],
    },
    {
        "id": "q3",
        "question": "What is the supply voltage required for the Hydraulic Power Unit?",
        "expected_answer": "24 VDC",
        "expected_conflict": False,
        "keywords": ["24", "vdc", "voltage"],
    },
    {
        "id": "q4",
        "question": "What is the tightening torque for the PRV-200 valve?",
        "expected_answer": "45 Nm",
        "expected_conflict": False,
        "keywords": ["torque", "45", "nm"],
    },
    {
        "id": "q5",
        "question": "What housing material is specified for the HPU-5000?",
        "expected_answer": "Stainless Steel 316L / Aluminum 6061-T6",
        "expected_conflict": True,
        "keywords": ["material", "steel", "aluminum"],
    },
]


@router.post("", response_model=EvaluationResponse)
async def run_evaluation(
    req: EvaluationRequest = EvaluationRequest(),
    session: AsyncSession = Depends(get_db),
) -> EvaluationResponse:
    """
    Run evaluation harness across benchmark questions.
    Evaluates factual accuracy, evidence grounding, conflict detection, and response latency.
    """
    global _LATEST_EVALUATION
    logger.info("Starting evaluation run with sample_size=%s", req.sample_size)
    run_start = time.time()

    suite = BENCHMARK_QUESTIONS[: req.sample_size or len(BENCHMARK_QUESTIONS)]
    results: List[QuestionResult] = []

    passed_count = 0
    total_latency = 0.0
    grounded_count = 0
    detected_conflicts_count = 0
    expected_conflicts_total = sum(1 for q in suite if q.get("expected_conflict"))

    for item in suite:
        q_start = time.time()
        q_text = item["question"]
        expected_ans = item["expected_answer"]
        expected_conflict = item.get("expected_conflict", False)

        # Execute query against knowledge system
        q_req = QueryRequest(
            question=q_text,
            top_k=5,
            include_conflicts=req.include_conflicts,
        )
        res = await query_knowledge(q_req, session=session)
        q_latency = round((time.time() - q_start) * 1000, 2)
        total_latency += q_latency

        ans_lower = res.answer.lower()
        # Assess keyword match
        matched_kws = [kw for kw in item.get("keywords", []) if kw.lower() in ans_lower]
        accuracy = min(1.0, len(matched_kws) / max(1, len(item.get("keywords", []))))

        # Evidence grounding score
        grounding_score = 1.0 if res.evidence else 0.0
        if res.evidence:
            grounded_count += 1

        # Conflict detection
        conflicts_detected = len(res.conflicts)
        if expected_conflict and conflicts_detected > 0:
            detected_conflicts_count += 1

        # Overall pass criteria: accurate and grounded
        passed = accuracy >= 0.5 and grounding_score > 0.0
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
    logger.info("Evaluation complete. Accuracy: %s, Grounding: %s", acc_ratio, grounding_ratio)
    return eval_response


@router.get("/results", response_model=EvaluationResponse)
async def get_evaluation_results(
    session: AsyncSession = Depends(get_db),
) -> EvaluationResponse:
    """Retrieve the latest evaluation benchmark results or execute an initial run if none exists."""
    global _LATEST_EVALUATION
    if _LATEST_EVALUATION:
        return EvaluationResponse.model_validate(_LATEST_EVALUATION)

    # If no evaluation was run yet, run one dynamically
    return await run_evaluation(EvaluationRequest(), session=session)
