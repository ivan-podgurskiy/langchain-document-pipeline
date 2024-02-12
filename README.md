# langchain-document-pipeline

> RAG pipeline for medical document processing with LangChain + Claude + pgvector

Work in progress.

## Goals

- Production-grade ingestion pipeline for medical PDFs
- Structured extraction of HCPCS codes, patient demographics, diagnoses
- pgvector-backed semantic search (no external vector DB)
- FastAPI service with ingestion, query, and cost tracking endpoints
- Evaluation pipeline with RAGAS metrics
