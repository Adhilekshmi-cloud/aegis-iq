# Aegis Knowledge System — Architecture

## Overview

The Aegis Knowledge System is an evidence-based AI knowledge ingestion and question-answering system designed for the Aegis Series-7 Hydraulic Control System. It ingests heterogeneous technical documentation, extracts structured facts with full provenance, resolves component aliases, manages conflicting and version-scoped information, and answers questions using only verifiable evidence.

## Architecture Diagram

```mermaid
flowchart TB
    subgraph input ["Document Ingestion"]
        DOCS["Raw Documents\n(PDF, HTML, XLSX, DOCX,\nPPTX, JSON, PNG)"]
        REG["Format-Specific\nExtractors"]
        NORM["Text & Unit\nNormalization"]
        CHUNK["Section-Aware\nChunking"]
        DOCS --> REG --> NORM --> CHUNK
    end

    subgraph processing ["Knowledge Processing"]
        FACT["Fact Extraction\n(Rules + Patterns + LLM)"]
        META["Metadata Extraction\n(Revision, Date, Trust)"]
        ENT["Entity Resolution\n(Exact → Normalized → Fuzzy)"]
        ALIAS["Alias Registry\n(Known mappings + HMI labels)"]
        CHUNK --> FACT & META
        FACT --> ENT
        ALIAS --> ENT
    end

    subgraph knowledge ["Knowledge Store (SQLite)"]
        DB[("SQLite Database")]
        ENTITIES["Entities\n& Aliases"]
        FACTS["Facts\n& Evidence"]
        CONFLICTS["Conflicts\n& Resolutions"]
        RELS["Relationships"]
        ENT --> ENTITIES
        FACT --> FACTS
        META --> DB
        ENTITIES & FACTS & CONFLICTS & RELS --> DB
    end

    subgraph conflict ["Conflict Analysis"]
        CD["Conflict Detector"]
        VS["Version Scope\nAnalysis"]
        TR["Trust Level\nComparison"]
        FACTS --> CD
        CD --> VS & TR --> CONFLICTS
    end

    subgraph retrieval ["Hybrid Retrieval"]
        EMBED["Sentence Transformers\n(all-MiniLM-L6-v2)"]
        FAISS["FAISS Vector\nIndex"]
        KW["SQLite Keyword\nSearch"]
        RRF["Reciprocal Rank\nFusion"]
        CHUNK --> EMBED --> FAISS
        DB --> KW
        FAISS & KW --> RRF
    end

    subgraph reasoning ["Answer Generation"]
        QA["Query Analyzer"]
        EA["Evidence Assembler"]
        AG["Answer Generator\n(LLM or Rule-based)"]
        CS["Confidence Scorer"]
        QA --> EA --> AG --> CS
    end

    subgraph api ["FastAPI Backend"]
        INGEST["/api/ingest"]
        QUERY["/api/query"]
        KNOW["/api/entities\n/api/facts\n/api/conflicts"]
        EVAL["/api/evaluate"]
    end

    subgraph ui ["React Frontend"]
        CHAT["Chat Interface"]
        EVPANEL["Evidence Panel"]
        KBROWSER["Knowledge Browser"]
        EBROWSER["Entity Browser"]
        IDASH["Ingestion Dashboard"]
        EDASH["Evaluation Dashboard"]
    end

    INGEST --> input
    QUERY --> QA
    RRF --> EA
    DB --> EA
    KNOW --> DB
    EVAL --> QA

    api --> ui
```

## Component Responsibilities

### Document Ingestion Layer
- **Extractor Registry**: Routes files to format-specific extractors based on file extension
- **Format Extractors**: 8 extractors (PDF, Scanned PDF/OCR, HTML, DOCX, XLSX, PPTX, JSON, PNG) each implementing a common `ExtractorProtocol`
- **Text Normalizer**: Standardizes whitespace, encoding, and control characters
- **Unit Normalizer**: Standardizes unit representations (PSI, °C, GPM, etc.)
- **Text Chunker**: Section-aware chunking with configurable overlap

### Knowledge Processing Layer
- **Fact Extractor**: Three-tier extraction: regex patterns → table parsing → LLM (when available)
- **Metadata Extractor**: Extracts revision numbers, dates, document IDs, and determines trust levels
- **Entity Resolver**: Four-tier resolution: exact match → deterministic normalization → alias registry → fuzzy matching
- **Alias Registry**: Maintains known component name/ID/HMI label mappings

### Knowledge Store
- **SQLite with SQLAlchemy**: Persistent storage for Documents, Entities, Facts, Evidence, Conflicts, Relationships
- **Full Provenance**: Every fact traces back to its source document, page, section, and source text
- **Conflict Detection**: Automatic detection of value mismatches, version differences, and source disagreements

### Retrieval Layer
- **Semantic Search**: Sentence Transformers embeddings indexed in FAISS
- **Keyword Search**: SQLite-based text matching on entities, facts, and chunks
- **Hybrid Retriever**: Reciprocal Rank Fusion combining semantic and keyword results

### Reasoning Layer
- **Query Analyzer**: Identifies entities, predicates, and question type from natural language
- **Evidence Assembler**: Gathers and ranks relevant facts by trust level and recency
- **Answer Generator**: LLM-grounded (when available) or rule-based answer construction
- **Confidence Scorer**: Multi-factor scoring based on evidence count, source trust, and agreement

## Data Flow

1. **Ingestion**: Raw documents → format extraction → normalization → chunking → fact extraction → entity resolution → conflict detection → persistent storage
2. **Indexing**: Document chunks → embedding → FAISS index (for semantic search)
3. **Querying**: Question → entity identification → hybrid retrieval → evidence assembly → conflict analysis → answer generation with citations
4. **Evaluation**: Predefined questions → query pipeline → metric calculation → report generation

## Knowledge Representation

### Provenance Model
Every answerable fact in the system traces back through:
```
Fact → Evidence → Document (with page, section, source text)
```

### Conflict Resolution
The system never silently resolves conflicts. Instead:
1. Facts are grouped by `(subject_entity, predicate)`
2. Differing values create `Conflict` records
3. Resolution is attempted via revision scope and trust levels
4. Unresolvable conflicts are preserved and surfaced to users

### Deterministic vs Model-Based Processing
| Stage | Deterministic | Model-Based |
|-------|--------------|-------------|
| Text extraction | All formats | OCR (Tesseract) |
| Fact extraction | Patterns, tables, JSON | Unstructured prose |
| Entity resolution | Exact, normalized, alias registry | Fuzzy matching |
| Answer generation | Structured fact lookup | Natural language synthesis |
| Conflict detection | All | None |
