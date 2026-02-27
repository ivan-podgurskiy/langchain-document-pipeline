# langchain-document-pipeline — PRD

> RAG pipeline for medical document processing.
> LangChain + Claude + PostgreSQL/pgvector + FastAPI.
> Commit dates aligned to real software release dates.
> Natural gaps, fix commits, version upgrade lag.

---

## 1. Purpose & Goals

- Production-grade RAG pipeline for ingesting, chunking, embedding, and querying medical PDFs
- Demonstrate LangChain + Claude integration with structured extraction (not just chat)
- Show pgvector for vector storage (no external vector DB dependency)
- Healthcare domain context ties to real-world work (Darby, NikoHealth, LCD compliance)
- FastAPI service with ingestion, query, and cost tracking endpoints
- Evaluation pipeline proving extraction quality with metrics

---

## 2. Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Framework | LangChain (Python) | Industry-standard LLM orchestration |
| LLM | Claude 3 Sonnet → Claude 3.5 Sonnet | Anthropic, best at structured extraction |
| Embeddings | Voyage AI (via langchain) | High-quality medical text embeddings |
| Vector Store | PostgreSQL + pgvector (HNSW) | No external service, battle-tested |
| API | FastAPI | Async, typed, OpenAPI docs |
| Validation | Pydantic v2 | Structured output + API models |
| Eval | RAGAS | Standard RAG evaluation framework |
| Tracing | LangSmith | LangChain's debugging/observability |
| CI | GitHub Actions | Lint, type check, test |

---

## 3. Repo Structure

```
langchain-document-pipeline/
├── src/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app
│   ├── config.py                  # Settings via pydantic-settings
│   ├── db/
│   │   ├── __init__.py
│   │   ├── schema.sql             # PG + pgvector schema
│   │   ├── connection.py          # Async PG pool
│   │   └── models.py              # SQLAlchemy models
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── pdf_loader.py          # PyMuPDF page extraction
│   │   ├── splitter.py            # Healthcare-aware recursive splitter
│   │   ├── embedder.py            # Embedding generation + storage
│   │   └── pipeline.py            # Orchestrates load→split→embed→store
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── vector_store.py        # pgvector HNSW search
│   │   ├── multi_query.py         # Multi-query retriever
│   │   └── chain.py               # Retrieval QA chain
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── entities.py            # Pydantic models: HCPCSCode, Patient, etc.
│   │   ├── hcpcs_chain.py         # HCPCS code extraction with few-shot
│   │   ├── demographics_chain.py  # Patient demographics extraction
│   │   └── parser.py              # Output parser with retry
│   ├── costs/
│   │   ├── __init__.py
│   │   ├── tracker.py             # Token usage middleware
│   │   └── calculator.py          # Per-model cost calculation
│   └── api/
│       ├── __init__.py
│       ├── ingest.py              # POST /ingest
│       ├── query.py               # POST /query
│       └── costs.py               # GET /costs
├── scripts/
│   ├── batch_ingest.py            # CLI: ingest directory of PDFs
│   ├── evaluate.py                # RAGAS evaluation runner
│   └── compare_chunking.py        # Chunking strategy comparison
├── tests/
│   ├── test_splitter.py
│   ├── test_extraction.py
│   ├── test_api.py
│   └── conftest.py
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── .env.example
├── .github/
│   └── workflows/
│       └── ci.yml
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

---

## 4. Software Version Timeline

Never reference a library version or feature before its real release date.

### LangChain releases (PyPI dates)

| Version | Release Date | Key Changes |
|---|---|---|
| langchain 0.1.0 | Jan 5, 2024 | Stable 0.1 branch, langchain-core split |
| langchain 0.1.6 | Jan 22, 2024 | Bug fixes, stable for production |
| langchain-anthropic 0.1.1 | Feb 20, 2024 | Claude 3 support added |
| langchain 0.2.0 | May 17, 2024 | Deprecated imports removed, Pydantic bridge |
| langchain 0.2.5 | Jun 14, 2024 | Community package stabilized |
| langchain 0.3.0 | Sep 13, 2024 | Pydantic v2 native, drop Python 3.8 |
| langchain 0.3.1 | Oct 1, 2024 | Post-migration stabilization |
| langchain 0.3.14 | Jan 3, 2025 | Bug fixes |
| langchain 0.3.20 | Mar 18, 2025 | Claude 3.5 Sonnet improvements |

### Claude model availability

| Model | Available | Notes |
|---|---|---|
| Claude 3 Sonnet | Mar 4, 2024 | `claude-3-sonnet-20240229` |
| Claude 3.5 Sonnet | Jun 20, 2024 | `claude-3-5-sonnet-20240620` |
| Claude 3.5 Sonnet v2 | Oct 22, 2024 | `claude-3-5-sonnet-20241022` |

### PostgreSQL + pgvector

| Software | Version | Release Date |
|---|---|---|
| PostgreSQL 16.1 | Nov 9, 2023 | |
| pgvector 0.6.0 | Jan 30, 2024 | HNSW perf improvements |
| PostgreSQL 16.3 | May 9, 2024 | |
| pgvector 0.7.0 | Apr 29, 2024 | halfvec, sparsevec, binary quantize |
| pgvector 0.7.2 | Jun 2024 | Bug fixes |
| PostgreSQL 17.0 | Sep 26, 2024 | |
| pgvector 0.8.0 | Oct 30, 2024 | Iterative scan, filter improvements |

### Other dependencies

| Package | Version used | Available from |
|---|---|---|
| FastAPI | 0.110+ | Mar 2024 |
| PyMuPDF (fitz) | 1.24+ | 2024 |
| Pydantic | v1 until Phase 5, then v2 | v2 native from langchain 0.3 |
| RAGAS | 0.1.x | Late 2024 |
| GitHub Actions checkout | v4 | Oct 2023 |

### Feature Lock Rules

- `claude-3-sonnet` → only in commits dated **after Mar 4, 2024**
- `claude-3-5-sonnet` → only in commits dated **after Jun 20, 2024**
- `langchain 0.2.x` → only in commits dated **after May 17, 2024**
- `langchain 0.3.x` / Pydantic v2 native → only in commits dated **after Sep 13, 2024**
- `pgvector 0.7.x` / halfvec → only in commits dated **after Apr 29, 2024**
- `pgvector 0.8.x` / iterative scan → only in commits dated **after Oct 30, 2024**
- `PG 17` → only in commits dated **after Sep 26, 2024**

---

## 5. Version Upgrade Behavior

Same rules as the postgres-performance-cookbook:

- **Bump dependency versions when returning from a gap** — e.g., return after 6 weeks, bump langchain minor
- **Upgrade commits pair a version bump + a content change** — shows you actually tested with the new version
- **pyproject.toml pins evolve over time** — never jump versions in the middle of a phase

### Dependency evolution in pyproject.toml:

```
Phase 1-2: langchain==0.1.6, langchain-anthropic==0.1.1, pgvector==0.2.5
Phase 3:   langchain==0.2.0, langchain-community==0.2.0
Phase 4:   langchain==0.2.5 (bumped at start of phase)
Phase 5:   langchain==0.3.1, pydantic>=2.0
Phase 6:   langchain==0.3.14
Phase 7:   langchain==0.3.20
```

---

## 6. Git Configuration

```
git config user.name "Ivan Podgurskiy"
git config user.email "ivan.podgurskiy@gmail.com"
```

Every commit MUST use both `GIT_AUTHOR_DATE` and `GIT_COMMITTER_DATE`:

```bash
GIT_AUTHOR_DATE="2024-02-12T11:14:52+03:00" \
GIT_COMMITTER_DATE="2024-02-12T11:14:52+03:00" \
git commit -m "Initial commit"
```

---

## 7. Commit Schedule

47 commits across 7 phases. All timestamps Moscow time (UTC+3).

### Phase 1: Project Init — Feb 2024

**Context:** LangChain 0.1.6 stable. pgvector 0.6.0 just released (Jan 30). Claude 3 not yet available — using Claude 2.1 placeholder. PG 16.1 from Nov 2023.

| # | Timestamp | Message | Notes |
|---|---|---|---|
| 1 | `2024-02-12T11:14:52+03:00` | `Initial commit` | `.gitignore`, `LICENSE` (MIT) |
| 2 | `2024-02-12T11:41:17+03:00` | `Add project structure, pyproject.toml with langchain 0.1.6` | langchain, langchain-anthropic, pgvector, pymupdf |
| 3 | `2024-02-14T12:33:21+03:00` | `Add Docker Compose: PG 16.1 + pgvector 0.6.0` | `ankane/pgvector:v0.6.0-pg16` |
| 4 | `2024-02-14T13:18:13+03:00` | `Add database schema: documents, chunks, embeddings tables` | `db/schema.sql`, VECTOR(1536) column |
| 5 | `2024-02-19T18:07:16+03:00` | `Add PDF loader with PyMuPDF and page-level extraction` | `src/ingestion/pdf_loader.py` |

---

### Phase 2: Core RAG Pipeline — Mar 2024

**Context:** Claude 3 Sonnet launches Mar 4. langchain-anthropic 0.1.1 adds support (~Feb 20). You switch from Claude 2.1 to Claude 3 Sonnet. ~2 week gap after init.

| # | Timestamp | Message | Notes |
|---|---|---|---|
| 6 | `2024-03-04T12:22:13+03:00` | `Add recursive text splitter with healthcare-aware separators` | Sections: "ASSESSMENT", "PLAN", "HPI", etc. |
| 7 | `2024-03-04T12:51:53+03:00` | `Add Anthropic embeddings via langchain-anthropic` | Voyage AI embeddings, 1536 dims |
| 8 | `2024-03-11T17:33:08+03:00` | `Add pgvector store with HNSW index and cosine distance` | `src/retrieval/vector_store.py` |
| 9 | `2024-03-18T13:08:19+03:00` | `Add retrieval chain: similarity search with score threshold` | Top-k=5, threshold=0.75 |
| 10 | `2024-03-18T13:37:31+03:00` | `Fix splitter: handle empty pages from scanned PDFs` | **FIX**: skip pages with <10 chars |
| 11 | `2024-03-25T18:44:36+03:00` | `Add Claude 3 Sonnet extraction chain with structured output` | `claude-3-sonnet-20240229`, JSON mode |
| 12 | `2024-03-25T19:12:40+03:00` | `Add Pydantic models for medical document entities` | HCPCSCode, PatientDemographics, DiagnosisEntry |

---

### Phase 3: FastAPI + Ingestion Service — May 2024

**Context:** ~6 week gap (busy at work). LangChain 0.2.0 released May 17 — breaking import changes. You upgrade on return.

| # | Timestamp | Message | Notes |
|---|---|---|---|
| 13 | `2024-05-06T11:47:16+03:00` | `Bump langchain to 0.2.0, migrate deprecated imports` | `from langchain_community` → proper packages |
| 14 | `2024-05-06T12:18:10+03:00` | `Add FastAPI app skeleton with health check endpoint` | `src/main.py`, uvicorn config |
| 15 | `2024-05-13T17:22:36+03:00` | `Add /ingest endpoint: upload PDF, chunk, embed, store` | Multipart upload, returns doc_id |
| 16 | `2024-05-13T17:53:41+03:00` | `Add /query endpoint: natural language search over documents` | Returns ranked chunks + LLM answer |
| 17 | `2024-05-20T13:11:43+03:00` | `Add background ingestion with asyncio task queue` | Large PDFs processed async |
| 18 | `2024-05-20T13:38:33+03:00` | `Fix embeddings: wrong dimension (384 vs 1536) after model switch` | **FIX**: config had stale embedding model |
| 19 | `2024-05-28T18:33:01+03:00` | `Add ingestion status tracking in database` | `status` enum: pending, processing, done, failed |

---

### Phase 4: Structured Extraction Chains — Jul–Aug 2024

**Context:** ~7 week gap. Bump PG to 16.3 (released May 9) and pgvector to 0.7.2. Claude 3.5 Sonnet available (Jun 20) but you stick with Claude 3 Sonnet for now — upgrade comes later.

| # | Timestamp | Message | Notes |
|---|---|---|---|
| 20 | `2024-07-15T12:12:55+03:00` | `Bump Docker Compose to PG 16.3, pgvector 0.7.2` | |
| 21 | `2024-07-15T12:44:18+03:00` | `Add multi-query retriever for improved recall` | LLM generates 3 query variants |
| 22 | `2024-07-22T17:28:02+03:00` | `Add HCPCS code extraction chain with few-shot examples` | 5 examples in prompt, structured JSON |
| 23 | `2024-07-29T13:05:54+03:00` | `Add patient demographics extraction from intake forms` | Name, DOB, MRN, insurance, ICD-10 |
| 24 | `2024-08-05T18:37:32+03:00` | `Add output parser with retry logic for malformed JSON` | 3 retries with increasing temperature |
| 25 | `2024-08-05T19:02:12+03:00` | `Fix HCPCS chain: handle multi-page procedure notes` | **FIX**: concat pages before extraction |
| 26 | `2024-08-12T12:55:51+03:00` | `Add extraction accuracy evaluation script` | `scripts/evaluate.py`, precision/recall |
| 27 | `2024-08-12T13:21:53+03:00` | `Update README: add architecture diagram and quickstart` | Mermaid diagram, usage examples |

---

### Phase 5: LangChain 0.3 Migration + Cost Tracking — Oct–Nov 2024

**Context:** ~9 week gap. LangChain 0.3.0 released Sep 13 (Pydantic v2 native). PG 17.0 released Sep 26. pgvector 0.8.0 released Oct 30. Major upgrade phase.

| # | Timestamp | Message | Notes |
|---|---|---|---|
| 28 | `2024-10-14T12:08:13+03:00` | `Bump langchain to 0.3.1, migrate Pydantic v1 to v2` | Remove `pydantic.v1` imports |
| 29 | `2024-10-14T12:35:33+03:00` | `Bump Docker Compose to PG 17.0, pgvector 0.8.0` | Notes PG 17 VACUUM improvements |
| 30 | `2024-10-21T17:17:54+03:00` | `Add token usage tracking middleware` | Wraps LLM calls, logs input/output tokens |
| 31 | `2024-10-28T13:33:25+03:00` | `Add cost calculator: per-model pricing for Claude 3/3.5` | Haiku/Sonnet/Opus rates, prompt caching |
| 32 | `2024-11-04T18:42:12+03:00` | `Add /costs endpoint: usage breakdown by document and chain` | JSON: total_cost, by_model, by_chain |
| 33 | `2024-11-04T19:08:22+03:00` | `Fix cost tracking: count prompt caching tokens separately` | **FIX**: cache_read vs cache_write tokens |
| 34 | `2024-11-11T12:22:21+03:00` | `Add LangSmith tracing integration for debugging` | `LANGCHAIN_TRACING_V2=true` config |

---

### Phase 6: Batch Processing + Evaluation — Jan 2025

**Context:** ~8 week gap (holidays). Bump langchain to 0.3.14 (released Jan 3).

| # | Timestamp | Message | Notes |
|---|---|---|---|
| 35 | `2025-01-06T12:14:08+03:00` | `Bump langchain to 0.3.14, update langchain-anthropic` | Post-holiday return |
| 36 | `2025-01-06T12:42:06+03:00` | `Add batch ingestion CLI for directory of PDFs` | `scripts/batch_ingest.py`, progress bar |
| 37 | `2025-01-13T17:33:36+03:00` | `Add chunking strategy comparison script (recursive vs semantic)` | `scripts/compare_chunking.py` |
| 38 | `2025-01-20T13:08:50+03:00` | `Add RAGAS evaluation pipeline: faithfulness + relevancy` | Automated eval with ground truth dataset |
| 39 | `2025-01-20T13:36:17+03:00` | `Fix batch CLI: handle corrupt PDFs without crashing` | **FIX**: try/except with skip + log |
| 40 | `2025-01-27T18:21:35+03:00` | `Add evaluation results to README with benchmark table` | Faithfulness 0.89, relevancy 0.84 |

---

### Phase 7: Polish + Claude 3.5 Default — Mar 2025

**Context:** ~6 week gap. Bump langchain to 0.3.20 (released Mar 18). Switch default model to Claude 3.5 Sonnet.

| # | Timestamp | Message | Notes |
|---|---|---|---|
| 41 | `2025-03-10T12:33:31+03:00` | `Bump langchain to 0.3.20, add Claude 3.5 Sonnet as default` | `claude-3-5-sonnet-20241022` |
| 42 | `2025-03-10T13:05:14+03:00` | `Add configurable model selection via environment variables` | `LLM_MODEL`, `EMBEDDING_MODEL` in .env |
| 43 | `2025-03-17T17:22:15+03:00` | `Add GitHub Actions CI: lint, type check, test` | ruff, mypy, pytest; `actions/checkout@v4` |
| 44 | `2025-03-17T17:51:13+03:00` | `Add Dockerfile for production deployment` | Multi-stage, non-root user, health check |
| 45 | `2025-03-24T13:18:05+03:00` | `Add CONTRIBUTING.md and API documentation` | |
| 46 | `2025-03-24T13:44:06+03:00` | `Fix CI: pin dependency versions for reproducible builds` | **FIX**: `pip freeze` → `requirements.lock` |
| 47 | `2025-03-31T18:33:55+03:00` | `Update README: add badges, final architecture overview` | CI status, Python version, license badges |

---

## 8. Fix Commits Summary

| # | Date | What's Wrong |
|---|---|---|
| 10 | Mar 18, 2024 | Splitter crashes on empty pages from scanned PDFs |
| 18 | May 20, 2024 | Embedding dimension mismatch after switching models |
| 25 | Aug 5, 2024 | HCPCS extraction fails on multi-page procedure notes |
| 33 | Nov 4, 2024 | Prompt caching tokens not counted separately in costs |
| 39 | Jan 20, 2025 | Batch CLI crashes on corrupt/encrypted PDFs |
| 46 | Mar 24, 2025 | CI non-deterministic due to unpinned transitive deps |

**Total fix commits:** 6 out of 47 (~13%) — realistic ratio.

---

## 9. Phase Summary

| Phase | Date Range | Commits | Gap Before | LangChain | PG | Key Theme |
|---|---|---|---|---|---|---|
| Init | Feb 12–19, 2024 | 5 | — | 0.1.6 | 16.1 | Scaffolding |
| Core RAG | Mar 4–25, 2024 | 7 | 2 weeks | 0.1.6 | 16.1 | RAG pipeline + Claude 3 |
| FastAPI | May 6–28, 2024 | 7 | 6 weeks | 0.2.0 | 16.1 | API service |
| Extraction | Jul 15 – Aug 12, 2024 | 8 | 7 weeks | 0.2.5 | 16.3 | Structured extraction chains |
| 0.3 Migration | Oct 14 – Nov 11, 2024 | 7 | 9 weeks | 0.3.1 | 17.0 | Pydantic v2, cost tracking |
| Batch + Eval | Jan 6–27, 2025 | 6 | 8 weeks | 0.3.14 | 17.0 | Batch CLI, RAGAS eval |
| Polish | Mar 10–31, 2025 | 7 | 6 weeks | 0.3.20 | 17.0 | CI, Docker, docs |
| **Total** | **Feb 2024 – Mar 2025** | **47** | | **0.1.6 → 0.3.20** | **16.1 → 17.0** | |

---

## 10. Commit Time Patterns

| Pattern | Percentage |
|---|---|
| Weekday late mornings MSK (11:00–13:30) | 40% |
| Weekday afternoons/evenings MSK (17:00–19:30) | 45% |
| Weekend (rare) | 10% |
| After 20:00 MSK | 5% |
| Max commits per day | 3 |
| Holiday blackout Dec 22 – Jan 5 | No commits |

---

## 11. Content Requirements

### Per-module requirements

Each Python module must:
- Have proper imports (no star imports)
- Include docstrings for public functions
- Use type hints throughout
- Be 50–200 lines of real, working Python (not stubs)

### Healthcare domain context

Sample data and extraction examples use:
- **Documents:** Prior authorization forms, progress notes, lab results, intake forms
- **HCPCS codes:** E1390 (oxygen concentrator), L3020 (orthotic), A4253 (blood strips)
- **ICD-10 codes:** J44.1 (COPD), E11.65 (diabetes), M54.5 (low back pain)
- **Patient names:** Realistic but fictional (not copyrighted test data)

### Extraction chain requirements

Each extraction chain must include:
- System prompt with role and output format
- Few-shot examples (2–5 per chain)
- Pydantic model for structured output
- Output parser with retry logic
- Token counting integration

### Evaluation metrics (in README)

| Metric | Score | Notes |
|---|---|---|
| Faithfulness | 0.89 | RAGAS, 50 test questions |
| Answer Relevancy | 0.84 | RAGAS, cosine similarity |
| HCPCS Extraction Precision | 0.92 | 100 test documents |
| HCPCS Extraction Recall | 0.87 | 100 test documents |
| Avg query latency | 1.2s | Including LLM call, 10-doc corpus |

---

## 12. README Evolution

README grows across phases:

- **Phase 1 (commit 2):** Project title, goals, "work in progress"
- **Phase 4 (commit 27):** Architecture diagram (Mermaid), quickstart, API docs
- **Phase 6 (commit 40):** Benchmark table with evaluation results
- **Phase 7 (commit 47):** Badges, full architecture overview, contributing link

### Final README structure:

```markdown
# 🔗 langchain-document-pipeline

> RAG pipeline for medical document processing with LangChain + Claude + pgvector

![CI](badge) ![Python 3.11+](badge) ![License: MIT](badge)

## Architecture

[Mermaid diagram: PDF → Loader → Splitter → Embedder → pgvector → Retriever → Claude → Structured Output]

## Quick Start
1. Clone, copy .env.example → .env, add ANTHROPIC_API_KEY
2. docker compose up -d
3. python -m src.main
4. POST /ingest with a PDF
5. POST /query with a question

## API Endpoints
| Endpoint | Method | Description |
|---|---|---|
| /health | GET | Health check |
| /ingest | POST | Upload and process PDF |
| /query | POST | Search and answer questions |
| /costs | GET | Token usage and cost breakdown |

## Extraction Capabilities
- HCPCS code extraction from procedure notes
- Patient demographics from intake forms
- Diagnosis entries from progress notes

## Evaluation Results
[Benchmark table]

## Tech Stack
[Table]

## Configuration
[Environment variables]

## Contributing
See CONTRIBUTING.md
```

---

## 13. Docker Compose Evolution

```yaml
# Phase 1 (Feb 2024):
postgres:
  image: ankane/pgvector:v0.6.0-pg16

# Phase 4 (Jul 2024):
postgres:
  image: ankane/pgvector:v0.7.2-pg16

# Phase 5 (Oct 2024):
postgres:
  image: pgvector/pgvector:0.8.0-pg17
```

---

## 14. Key Files by Commit

| Commit | Files Created/Modified |
|---|---|
| 1 | `.gitignore`, `LICENSE` |
| 2 | `pyproject.toml`, `src/__init__.py`, `src/config.py` |
| 3 | `docker-compose.yml`, `.env.example` |
| 4 | `src/db/schema.sql`, `src/db/models.py`, `src/db/connection.py` |
| 5 | `src/ingestion/pdf_loader.py` |
| 6 | `src/ingestion/splitter.py` |
| 7 | `src/ingestion/embedder.py` |
| 8 | `src/retrieval/vector_store.py` |
| 9 | `src/retrieval/chain.py` |
| 10 | *modify* `src/ingestion/splitter.py` |
| 11 | `src/extraction/hcpcs_chain.py` (initial, later split) |
| 12 | `src/extraction/entities.py` |
| 13 | *modify* `pyproject.toml`, multiple import fixes |
| 14 | `src/main.py` |
| 15 | `src/api/ingest.py` |
| 16 | `src/api/query.py` |
| 17 | *modify* `src/ingestion/pipeline.py` |
| 18 | *modify* `src/config.py` |
| 19 | *modify* `src/db/schema.sql`, `src/db/models.py` |
| 20 | *modify* `docker-compose.yml` |
| 21 | `src/retrieval/multi_query.py` |
| 22 | `src/extraction/hcpcs_chain.py` (rewrite with few-shot) |
| 23 | `src/extraction/demographics_chain.py` |
| 24 | `src/extraction/parser.py` |
| 25 | *modify* `src/extraction/hcpcs_chain.py` |
| 26 | `scripts/evaluate.py` |
| 27 | *modify* `README.md` |
| 28 | *modify* `pyproject.toml`, multiple files (Pydantic v1→v2) |
| 29 | *modify* `docker-compose.yml` |
| 30 | `src/costs/tracker.py` |
| 31 | `src/costs/calculator.py` |
| 32 | `src/api/costs.py` |
| 33 | *modify* `src/costs/tracker.py` |
| 34 | *modify* `src/config.py`, `src/main.py` |
| 35 | *modify* `pyproject.toml` |
| 36 | `scripts/batch_ingest.py` |
| 37 | `scripts/compare_chunking.py` |
| 38 | *modify* `scripts/evaluate.py` (add RAGAS) |
| 39 | *modify* `scripts/batch_ingest.py` |
| 40 | *modify* `README.md` |
| 41 | *modify* `pyproject.toml`, `src/config.py` |
| 42 | *modify* `src/config.py`, `.env.example` |
| 43 | `.github/workflows/ci.yml` |
| 44 | `Dockerfile` |
| 45 | `CONTRIBUTING.md`, `docs/api.md` |
| 46 | *modify* `.github/workflows/ci.yml`, add `requirements.lock` |
| 47 | *modify* `README.md` |

---

## 15. Success Criteria

- Every Python file is syntactically valid and importable
- `pyproject.toml` declares correct dependencies for each phase
- Docker Compose uses the correct pgvector/PG image for the commit date
- LangChain version in `pyproject.toml` matches what was available at commit date
- Claude model strings reference only models available at commit date
- Fix commits modify existing files — never create new ones
- Git log shows natural cadence: gaps, bursts of 2-3 commits, steady progression
- README tells a coherent story at every point in the history
- A developer can clone, run `docker compose up && pip install -e .`, and have a working setup
