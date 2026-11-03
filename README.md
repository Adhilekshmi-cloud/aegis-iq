# Aegis Knowledge System

An evidence-based AI knowledge ingestion and question-answering system for the **Aegis Series-7 Hydraulic Control System**.

The system ingests heterogeneous technical documentation (8 formats), extracts structured facts with full source provenance, resolves component aliases, manages conflicting and version-scoped information, and answers questions using only verifiable evidence.

---

## Key Features

- **Multi-format ingestion**: PDF, scanned PDF (OCR), HTML, XLSX, DOCX, PPTX, JSON, PNG
- **Provenance-preserving knowledge store**: Every fact traces to its source document, page, and section
- **Entity resolution**: Component names, IDs, HMI labels, and legacy names unified
- **Conflict detection**: Contradictions between documents are detected, preserved, and surfaced
- **Version-aware facts**: Revision scope and ECN tracking for specification changes
- **Evidence-grounded QA**: Answers cite only verified evidence; never fabricates
- **Hybrid retrieval**: Semantic (FAISS) + keyword search combined with Reciprocal Rank Fusion
- **Evaluation harness**: Automated testing against predefined questions with quantitative metrics

---

## Architecture

```
Raw Documents → Format Extraction → Normalization → Entity Resolution
→ Fact Extraction → Conflict Detection → Knowledge Store
→ Hybrid Retrieval → Evidence-Grounded Answer Generation
```

See [docs/architecture.md](docs/architecture.md) for the full architecture diagram.

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- (Optional) Tesseract OCR for scanned documents
- (Optional) OpenAI API key for LLM-enhanced answers

### 1. Clone and configure

```bash
cd aegis-knowledge-system
cp .env.example .env
# Edit .env to add your OpenAI API key (optional)
```

### 2. Backend setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
```

### 3. Frontend setup

```bash
cd frontend
npm install
```

### 4. Start the backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 5. Start the frontend

```bash
cd frontend
npm run dev
```

### 6. Ingest documents

```bash
# Via API
curl -X POST http://localhost:8000/api/ingest

# Or use the Ingest button in the web UI at http://localhost:5173
```

### 7. Ask questions

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the operating pressure of the Aegis Series-7?"}'
```

### 8. Run evaluation

```bash
curl -X POST http://localhost:8000/api/evaluate
curl http://localhost:8000/api/evaluate/results
```

### 9. Run tests

```bash
cd backend
python -m pytest tests/ -v
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | _(empty)_ | OpenAI API key (optional, enables LLM answers) |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Any OpenAI-compatible endpoint |
| `OPENAI_MODEL` | `gpt-4o-mini` | LLM model name |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence Transformers model |
| `DATABASE_URL` | `sqlite+aiosqlite:///./aegis_knowledge.db` | Database connection |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins |
| `DATA_DIR` | `../data/aegis-dataset` | Path to documents |
| `LOG_LEVEL` | `INFO` | Logging level |
| `FAISS_INDEX_PATH` | `./faiss_index` | FAISS index storage path |

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/ingest` | Ingest all documents from data directory |
| `GET` | `/api/ingest/status` | Ingestion status and report |
| `POST` | `/api/query` | Submit natural language question |
| `GET` | `/api/entities` | List all entities with aliases |
| `GET` | `/api/entities/{id}` | Entity details with facts |
| `GET` | `/api/facts` | List facts (filterable) |
| `GET` | `/api/facts/{id}` | Fact detail with evidence |
| `GET` | `/api/conflicts` | List all detected conflicts |
| `GET` | `/api/documents` | List ingested documents |
| `POST` | `/api/evaluate` | Run evaluation harness |
| `GET` | `/api/evaluate/results` | Get evaluation results |
| `GET` | `/api/health` | Health check |

Full API docs: http://localhost:8000/docs (Swagger UI)

---

## Project Structure

```
aegis-knowledge-system/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI route handlers
│   │   ├── ingestion/        # Format-specific document extractors
│   │   ├── extraction/       # Fact and metadata extraction
│   │   ├── normalization/    # Text and unit normalization
│   │   ├── entity_resolution/ # Component alias resolution
│   │   ├── knowledge/        # SQLAlchemy models, schemas, repository
│   │   ├── retrieval/        # FAISS + keyword hybrid retrieval
│   │   ├── reasoning/        # Query analysis and answer generation
│   │   ├── evaluation/       # Evaluation harness and metrics
│   │   └── main.py           # FastAPI application entry point
│   ├── tests/                # Pytest test suite
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/       # React UI components
│       ├── services/         # API client
│       ├── types/            # TypeScript interfaces
│       └── App.tsx           # Route configuration
├── data/
│   └── aegis-dataset/        # Source documents (8 formats)
├── evaluation/
│   ├── evaluation_questions.json
│   └── results/              # Evaluation outputs
├── docs/
│   ├── architecture.md
│   ├── design_decisions.md
│   └── evaluation_report.md
├── .env.example
└── README.md
```

---

## Documentation

- [Architecture](docs/architecture.md) — System architecture, data flow, component responsibilities
- [Design Decisions](docs/design_decisions.md) — Technical trade-offs and rationale
- [Evaluation Report](docs/evaluation_report.md) — Methodology, metrics, and results

---

## Limitations

1. **Synthetic dataset**: The Aegis Series-7 documentation is synthetic (no real dataset was provided)
2. **OCR**: Requires Tesseract for scanned documents; gracefully degrades without it
3. **LLM**: Enhanced answers require an OpenAI API key; falls back to rule-based extraction
4. **Single-user**: No authentication or multi-tenancy
5. **Scale**: Designed for 10-20 technical documents, not thousands

---

## License

MIT
