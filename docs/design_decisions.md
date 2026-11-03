# Aegis Knowledge System — Design Decisions

## 1. SQLite over PostgreSQL

**Decision**: Use SQLite with aiosqlite for the knowledge store.

**Rationale**: The project specification requires SQLite. While PostgreSQL would provide better concurrency and native vector search (pgvector), SQLite offers:
- Zero-configuration deployment
- Single-file database for portability
- Sufficient performance for the document scale (10-20 documents)
- No external service dependency

**Trade-off**: No native vector search — FAISS handles this separately. No full-text search indexes — we implement keyword matching in application code.

## 2. FAISS over SQLite-native Vector Search

**Decision**: Use FAISS (Facebook AI Similarity Search) for semantic retrieval.

**Rationale**: SQLite has no native vector search capability. FAISS provides:
- Highly optimized approximate nearest neighbor search
- CPU-only operation (no GPU required)
- Persistent index save/load
- Well-tested at scale

**Alternative considered**: sqlite-vss extension — rejected due to limited availability and maturity.

## 3. Sentence Transformers over OpenAI Embeddings

**Decision**: Use local Sentence Transformers (all-MiniLM-L6-v2) for embeddings.

**Rationale**:
- No API key required for core functionality
- Deterministic results (no network dependency)
- Fast inference on CPU
- 384-dimensional vectors (compact, efficient)
- Good quality for technical documentation retrieval

**Trade-off**: Lower dimensionality and quality than OpenAI text-embedding-3-small (1536-dim), but sufficient for domain-specific retrieval.

## 4. Rules-First Fact Extraction

**Decision**: Deterministic pattern matching and table parsing as primary extraction, LLM as optional fallback.

**Rationale**: Technical documentation follows predictable patterns:
- Specifications use "parameter: value unit" format
- Tables map directly to (subject, predicate, value, unit) tuples
- JSON documents have explicit key-value structure
- ECNs follow structured change description formats

Rule-based extraction provides:
- 100% reproducibility
- No API cost
- Traceable extraction method
- Higher precision for structured content

**Trade-off**: Lower recall for unstructured prose. LLM extraction fills this gap when available.

## 5. Three-Tier Entity Resolution

**Decision**: Exact match → deterministic normalization → fuzzy matching (with high threshold).

**Rationale**: Most entity matches in technical documentation are deterministic:
- Component IDs follow XX-#### patterns
- HMI labels map directly to component IDs
- Known abbreviations expand unambiguously

Fuzzy matching (threshold > 0.85) catches edge cases without creating false merges.

**Critical decision**: Ambiguous matches (confidence < 0.85) are **never auto-merged** — they are flagged for human review.

## 6. Never Silent Conflict Resolution

**Decision**: All conflicting values are preserved; resolution metadata explains the relationship.

**Rationale**: In safety-critical hydraulic systems, silently choosing one specification over another could be dangerous. The system:
- Preserves all values with their provenance
- Records the conflict type and involved facts
- Attempts resolution through revision scope and trust level
- Explicitly marks unresolvable conflicts
- Surfaces conflicts to users in answers

**Trade-off**: More complex answers, but never misleading.

## 7. Trust Level Hierarchy

**Decision**: Documents are assigned trust levels based on type, not recency.

| Trust Level | Document Types |
|-------------|---------------|
| HIGH | Official manuals, ECNs, technical bulletins, OEM specs |
| MEDIUM | Maintenance guides, QA reports, training materials |
| LOW | Field notes, informal communications |

**Rationale**: An engineering change notice from a chief engineer supersedes field technician observations, regardless of dates. Recency is used only to determine revision scope within the same trust level.

## 8. Confidence Scoring Model

**Decision**: Multi-factor confidence scoring.

Factors:
- **Evidence count**: More independent sources = higher confidence
- **Source trust**: High-trust sources contribute more
- **Agreement**: All sources agree = higher confidence; conflicts = lower
- **Extraction method**: Rule/pattern > table > LLM
- **Freshness**: More recent revisions weighted slightly higher

Score range: 0.0 (no evidence) to 1.0 (multiple high-trust sources in agreement).

## 9. Synthetic Dataset

**Decision**: Create a realistic synthetic dataset since no real Aegis dataset was provided.

**Design principles**:
- Specifications are internally consistent within each document
- Deliberate cross-document conflicts exercise conflict detection
- Version-scoped changes (Rev A → Rev B) exercise revision tracking
- Multiple naming conventions exercise entity resolution
- One irrelevant document exercises noise filtering

**Limitation**: Real-world documentation would likely have more subtle conflicts and ambiguities. The synthetic dataset exercises all features but may overrepresent certain patterns.

## 10. Frontend Technology Choice

**Decision**: React + Vite + TypeScript + Tailwind CSS.

**Rationale**: Per specification requirements. Vite provides fast HMR for development. TypeScript ensures type safety with the backend API contract. Tailwind enables rapid, consistent styling.

## Known Limitations

1. **No real Aegis dataset**: All facts, specifications, and documents are synthetic
2. **OCR requires Tesseract**: Scanned PDF and image processing fails gracefully without Tesseract
3. **LLM-dependent features**: Answer generation quality degrades without an LLM API key (falls back to structured fact lookup)
4. **Single-user**: No authentication or multi-tenancy
5. **Memory-bound FAISS**: Index lives in memory; large document sets may require disk-based index
6. **No incremental ingestion**: Re-ingestion processes all documents (could be optimized with change detection)
