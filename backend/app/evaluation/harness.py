"""Evaluation harness - runs evaluation questions through the QA pipeline."""

import json
import logging
import time
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.reasoning.query_analyzer import QueryAnalyzer
from app.reasoning.evidence_assembler import EvidenceAssembler
from app.reasoning.answer_generator import AnswerGenerator
from app.evaluation.metrics import (
    QuestionMetrics, AggregateMetrics,
    check_answer_correctness, check_conflict_handling,
    check_abstention, calculate_evidence_precision,
    calculate_evidence_recall, calculate_aggregate_metrics,
)

logger = logging.getLogger(__name__)


class EvaluationHarness:
    """Runs evaluation questions through the full QA pipeline and measures performance."""

    def __init__(self, questions_path: Optional[str] = None):
        """Initialize the evaluation harness.
        
        Args:
            questions_path: Path to evaluation_questions.json. 
                           Defaults to ../evaluation/evaluation_questions.json.
        """
        if questions_path:
            self.questions_path = Path(questions_path)
        else:
            self.questions_path = (
                Path(__file__).parent.parent.parent.parent / 
                "evaluation" / "evaluation_questions.json"
            )
        
        self.analyzer = QueryAnalyzer()
        self.assembler = EvidenceAssembler()
        self.generator = AnswerGenerator()
    
    def load_questions(self) -> list[dict]:
        """Load evaluation questions from JSON file.
        
        Returns:
            List of question dictionaries.
            
        Raises:
            FileNotFoundError: If the questions file doesn't exist.
        """
        if not self.questions_path.exists():
            logger.error(f"Evaluation questions not found: {self.questions_path}")
            raise FileNotFoundError(
                f"Evaluation questions file not found: {self.questions_path}"
            )
        
        with open(self.questions_path, "r", encoding="utf-8") as f:
            questions = json.load(f)
        
        logger.info(f"Loaded {len(questions)} evaluation questions")
        return questions

    async def run(self, db: AsyncSession) -> tuple[list[QuestionMetrics], AggregateMetrics]:
        """Run the full evaluation harness.
        
        Args:
            db: Database session with ingested knowledge.
            
        Returns:
            Tuple of (per-question metrics, aggregate metrics).
        """
        questions = self.load_questions()
        all_metrics: list[QuestionMetrics] = []
        
        for q in questions:
            logger.info(f"Evaluating {q['id']}: {q['question'][:60]}...")
            
            try:
                metrics = await self._evaluate_question(db, q)
                all_metrics.append(metrics)
                logger.info(
                    f"  {q['id']}: correct={metrics.answer_correct}, "
                    f"overlap={metrics.keyword_overlap:.2f}, "
                    f"latency={metrics.latency_seconds:.2f}s"
                )
            except Exception as e:
                logger.error(f"  {q['id']}: FAILED - {e}")
                all_metrics.append(QuestionMetrics(
                    question_id=q["id"],
                    question=q["question"],
                    expected_answer=q.get("expected_answer", ""),
                    actual_answer=f"ERROR: {str(e)}",
                    expected_behavior=q.get("expected_behavior", ""),
                    requires_conflict_handling=q.get("requires_conflict_handling", False),
                ))
        
        aggregate = calculate_aggregate_metrics(all_metrics)
        
        logger.info(
            f"Evaluation complete: accuracy={aggregate.answer_accuracy:.2%}, "
            f"conflict_handling={aggregate.conflict_handling_accuracy:.2%}, "
            f"avg_latency={aggregate.avg_latency:.2f}s"
        )
        
        return all_metrics, aggregate

    async def _evaluate_question(
        self, db: AsyncSession, question: dict
    ) -> QuestionMetrics:
        """Evaluate a single question.
        
        Args:
            db: Database session.
            question: Question dict from evaluation_questions.json.
            
        Returns:
            QuestionMetrics for this question.
        """
        start_time = time.time()
        
        # Run through the full pipeline
        analysis = self.analyzer.analyze(question["question"])
        evidence = await self.assembler.assemble(db, analysis)
        answer = await self.generator.generate(evidence)
        
        latency = time.time() - start_time
        
        expected = question.get("expected_answer", "")
        expected_behavior = question.get("expected_behavior", "")
        requires_conflict = question.get("requires_conflict_handling", False)
        relevant_docs = question.get("relevant_documents", [])
        
        # Check correctness
        exact, partial, overlap = check_answer_correctness(expected, answer.answer)
        
        # Get cited documents from claims
        cited_docs = []
        for claim in answer.claims:
            for ev in claim.evidence:
                if ev.document and ev.document not in cited_docs:
                    cited_docs.append(ev.document)
        
        # Check conflict handling
        conflict_handled = False
        if requires_conflict:
            conflict_dicts = [
                {"description": c.description, "values": c.values}
                for c in answer.conflicts
            ]
            conflict_handled = check_conflict_handling(answer.answer, conflict_dicts)
        
        # Check abstention
        abstention_correct = False
        if expected_behavior == "appropriate_abstention":
            abstention_correct = check_abstention(answer.answer)
            # For abstention questions, correct abstention = correct answer
            if abstention_correct:
                exact = True
                partial = True
        
        # Evidence precision/recall
        precision = calculate_evidence_precision(cited_docs, relevant_docs)
        recall = calculate_evidence_recall(cited_docs, relevant_docs)
        
        # Citation accuracy (simplified: check if any cited doc is in relevant list)
        citation_accurate = precision > 0 if relevant_docs else True
        
        return QuestionMetrics(
            question_id=question["id"],
            question=question["question"],
            expected_answer=expected,
            actual_answer=answer.answer,
            answer_correct=exact,
            answer_partial=partial,
            evidence_precision=precision,
            evidence_recall=recall,
            citation_accurate=citation_accurate,
            conflict_handled=conflict_handled,
            abstention_correct=abstention_correct,
            latency_seconds=latency,
            requires_conflict_handling=requires_conflict,
            expected_behavior=expected_behavior,
            keyword_overlap=overlap,
        )
