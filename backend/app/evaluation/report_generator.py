"""Evaluation report generator - outputs results in JSON, CSV, and Markdown."""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.evaluation.metrics import QuestionMetrics, AggregateMetrics

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates evaluation reports in multiple formats."""

    def __init__(self, output_dir: Optional[str] = None):
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = (
                Path(__file__).parent.parent.parent.parent /
                "evaluation" / "results"
            )
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_all(
        self,
        question_metrics: list[QuestionMetrics],
        aggregate: AggregateMetrics,
    ) -> dict[str, str]:
        """Generate all report formats.
        
        Args:
            question_metrics: Per-question results.
            aggregate: Aggregate metrics.
            
        Returns:
            Dict mapping format name to output file path.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        json_path = self.generate_json(question_metrics, aggregate, timestamp)
        csv_path = self.generate_csv(question_metrics, aggregate, timestamp)
        md_path = self.generate_markdown(question_metrics, aggregate, timestamp)
        
        return {
            "json": str(json_path),
            "csv": str(csv_path),
            "markdown": str(md_path),
        }

    def generate_json(
        self,
        question_metrics: list[QuestionMetrics],
        aggregate: AggregateMetrics,
        timestamp: str = "",
    ) -> Path:
        """Generate JSON evaluation results."""
        if not timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        output = {
            "timestamp": timestamp,
            "aggregate_metrics": {
                "answer_accuracy": round(aggregate.answer_accuracy, 4),
                "partial_accuracy": round(aggregate.partial_accuracy, 4),
                "evidence_precision": round(aggregate.evidence_precision, 4),
                "evidence_recall": round(aggregate.evidence_recall, 4),
                "citation_accuracy": round(aggregate.citation_accuracy, 4),
                "conflict_handling_accuracy": round(aggregate.conflict_handling_accuracy, 4),
                "abstention_rate": round(aggregate.abstention_rate, 4),
                "avg_latency_seconds": round(aggregate.avg_latency, 4),
                "total_questions": aggregate.total_questions,
                "questions_answered": aggregate.questions_answered,
            },
            "per_question_results": [
                {
                    "question_id": m.question_id,
                    "question": m.question,
                    "expected_answer": m.expected_answer,
                    "actual_answer": m.actual_answer,
                    "answer_correct": m.answer_correct,
                    "answer_partial": m.answer_partial,
                    "keyword_overlap": round(m.keyword_overlap, 4),
                    "evidence_precision": round(m.evidence_precision, 4),
                    "evidence_recall": round(m.evidence_recall, 4),
                    "citation_accurate": m.citation_accurate,
                    "conflict_handled": m.conflict_handled,
                    "abstention_correct": m.abstention_correct,
                    "latency_seconds": round(m.latency_seconds, 4),
                    "expected_behavior": m.expected_behavior,
                    "requires_conflict_handling": m.requires_conflict_handling,
                }
                for m in question_metrics
            ]
        }
        
        path = self.output_dir / f"evaluation_results_{timestamp}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        # Also save as latest
        latest_path = self.output_dir / "evaluation_results_latest.json"
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        logger.info(f"JSON report saved: {path}")
        return path

    def generate_csv(
        self,
        question_metrics: list[QuestionMetrics],
        aggregate: AggregateMetrics,
        timestamp: str = "",
    ) -> Path:
        """Generate CSV evaluation results."""
        if not timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        path = self.output_dir / f"evaluation_results_{timestamp}.csv"
        
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Question ID", "Question", "Expected", "Actual",
                "Correct", "Partial", "Overlap", "Evidence Precision",
                "Evidence Recall", "Citation Accurate", "Conflict Handled",
                "Abstention Correct", "Latency (s)", "Expected Behavior",
            ])
            
            for m in question_metrics:
                writer.writerow([
                    m.question_id, m.question, m.expected_answer[:100],
                    m.actual_answer[:100],
                    m.answer_correct, m.answer_partial,
                    f"{m.keyword_overlap:.2f}",
                    f"{m.evidence_precision:.2f}",
                    f"{m.evidence_recall:.2f}",
                    m.citation_accurate, m.conflict_handled,
                    m.abstention_correct, f"{m.latency_seconds:.2f}",
                    m.expected_behavior,
                ])
        
        logger.info(f"CSV report saved: {path}")
        return path

    def generate_markdown(
        self,
        question_metrics: list[QuestionMetrics],
        aggregate: AggregateMetrics,
        timestamp: str = "",
    ) -> Path:
        """Generate Markdown evaluation report."""
        if not timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        lines = [
            "# Aegis Knowledge System — Evaluation Results",
            f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\n## Aggregate Metrics\n",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Answer Accuracy | {aggregate.answer_accuracy:.1%} |",
            f"| Partial Accuracy | {aggregate.partial_accuracy:.1%} |",
            f"| Evidence Precision | {aggregate.evidence_precision:.1%} |",
            f"| Evidence Recall | {aggregate.evidence_recall:.1%} |",
            f"| Citation Accuracy | {aggregate.citation_accuracy:.1%} |",
            f"| Conflict Handling | {aggregate.conflict_handling_accuracy:.1%} |",
            f"| Abstention Rate | {aggregate.abstention_rate:.1%} |",
            f"| Avg Latency | {aggregate.avg_latency:.2f}s |",
            f"| Total Questions | {aggregate.total_questions} |",
            "",
            "## Per-Question Results\n",
            "| ID | Question | Correct | Overlap | Latency |",
            "|----|----------|---------|---------|---------|",
        ]
        
        for m in question_metrics:
            status = "✅" if m.answer_correct else ("🟡" if m.answer_partial else "❌")
            q_short = m.question[:50] + "..." if len(m.question) > 50 else m.question
            lines.append(
                f"| {m.question_id} | {q_short} | {status} | "
                f"{m.keyword_overlap:.0%} | {m.latency_seconds:.2f}s |"
            )
        
        lines.extend([
            "",
            "## Detailed Results\n",
        ])
        
        for m in question_metrics:
            status = "✅ Correct" if m.answer_correct else (
                "🟡 Partial" if m.answer_partial else "❌ Incorrect"
            )
            lines.extend([
                f"### {m.question_id}: {m.question}\n",
                f"**Status**: {status} (overlap: {m.keyword_overlap:.0%})",
                f"\n**Expected**: {m.expected_answer[:200]}",
                f"\n**Actual**: {m.actual_answer[:200]}",
                "",
            ])
        
        path = self.output_dir / f"evaluation_report_{timestamp}.md"
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        logger.info(f"Markdown report saved: {path}")
        return path
