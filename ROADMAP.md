# Roadmap

This document tracks planned work after **v0.1.0**. The historical build plan lives in
[`langchain-document-pipeline-PRD .md`](langchain-document-pipeline-PRD%20.md); this file is the
living backlog.

## Shipped (v0.1.0)

- PDF ingest → healthcare-aware chunking → Voyage embeddings → pgvector (HNSW)
- RAG query API (`POST /query/`) with Claude
- HCPCS and demographics extraction chains (library + eval script)
- Cost tracking API and dashboard (documents, upload, query, costs)
- CI: ruff, mypy, Docker build; release-please

## Now (open PRs / in progress)

| Item | Branch / PR | Notes |
|------|-------------|--------|
| Python 3.11 dev setup + DB health check | `fix/local-dev-python311` | `setup_dev.sh`, `.python-version`, `/health` probes Postgres |
| Unit tests + sample eval CSV | `feat/tests-and-eval-sample` | CI pytest; `data/eval_sample.csv` |

## Next (high priority)

### Quality & DX

- [ ] Merge test PR and keep coverage trending up (integration tests with real Postgres in CI)
- [ ] Align `ExtractionResult.extraction_model` default with `settings.llm_model`
- [ ] Reduce mypy `disable_error_code` overrides module-by-module

### Product gaps (README vs code)

- [ ] **`POST /extract`** (or run-on-ingest) for HCPCS / demographics — chains exist but are not exposed via API or UI
- [ ] Wire **multi-query retriever** into `answer_question` or update architecture docs
- [ ] Dedicated **ICD-10 extraction chain** or narrow README to “ICD-10 via demographics chain”
- [ ] Expand **`data/eval_sample.csv`** → full eval set; publish reproducible eval script output

### Dashboard

- [ ] Ingest status polling in UI
- [ ] Extraction results view per document
- [ ] Markdown rendering for RAG answers; optional streaming
- [ ] Responsive layout / basic a11y (focus, labels)

## Later (medium priority)

- [ ] FastAPI **lifespan** handler (replace deprecated `on_event`)
- [ ] Authn for production deployments
- [ ] Support non-PDF sources (plain text, DOCX)
- [ ] Configurable domain pack (prompts, separators, entity schemas) for non-medical corpora
- [ ] LangSmith trace links in dashboard when tracing is enabled

## Ideas (low priority / exploratory)

- [ ] Batch extraction CLI parallel to `batch_ingest.py`
- [ ] Read replicas / connection pooling tuning for larger corpora
- [ ] OIDC / API keys for multi-tenant ingest

## How to contribute

Pick an unchecked item, open an issue or comment on the roadmap PR, and follow
[CONTRIBUTING.md](CONTRIBUTING.md). Prefer small, reviewable PRs aligned with one roadmap row.
