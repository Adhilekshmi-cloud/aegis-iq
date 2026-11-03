# Aegis Knowledge System — Evaluation Report

## Methodology

The evaluation harness tests the system's ability to correctly answer questions about the Aegis Series-7 Hydraulic Control System based solely on ingested documentation. Questions are drawn from `evaluation/evaluation_questions.json` and cover:

- **Direct fact lookup**: Single-source answers from structured data
- **Conflict detection**: Questions where documents disagree
- **Version awareness**: Questions requiring revision-scoped answers
- **Alias resolution**: Questions using non-canonical component names
- **Appropriate abstention**: Questions with no available evidence
- **Multi-source synthesis**: Answers requiring information from multiple documents
- **Noise filtering**: Questions touching irrelevant (superseded) documentation

## Metric Definitions

| Metric | Definition |
|--------|-----------|
| **Answer Accuracy** | Fraction of questions where the answer contains the key expected information |
| **Evidence Precision** | Fraction of cited evidence items that are actually relevant to the answer |
| **Evidence Recall** | Fraction of relevant documents cited out of all documents that should be cited |
| **Citation Accuracy** | Fraction of citations with correct document name and page/section references |
| **Conflict Handling** | Fraction of conflict-bearing questions where all conflicting values are surfaced |
| **Abstention Rate** | Fraction of unanswerable questions where the system correctly abstains |
| **Avg Latency** | Average end-to-end response time per question (seconds) |

## Evaluation Limitations

1. **Synthetic ground truth**: Expected answers are based on the synthetic dataset, not independently verified technical specifications
2. **Keyword matching**: Answer accuracy uses keyword overlap, which may miss semantically equivalent phrasing
3. **Small question set**: 15 questions provide directional metrics but not statistical significance
4. **No human evaluation**: No human judges assessed answer quality or readability

## Results

> [!NOTE]
> Results will be populated after the evaluation harness is executed against the ingested dataset. Run `POST /api/evaluate` to generate results.

### Aggregate Metrics

| Metric | Value |
|--------|-------|
| Answer Accuracy | _pending_ |
| Evidence Precision | _pending_ |
| Evidence Recall | _pending_ |
| Citation Accuracy | _pending_ |
| Conflict Handling | _pending_ |
| Abstention Rate | _pending_ |
| Avg Latency | _pending_ |

### Per-Question Results

_Results table will be generated after evaluation execution._

### Failure Analysis

_Failure analysis will be generated after evaluation execution._
