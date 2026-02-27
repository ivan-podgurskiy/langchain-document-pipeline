# API Reference

Full interactive documentation is available at `/docs` (Swagger UI) and `/redoc` when the service is running.

## Authentication

All endpoints require the service to be configured with a valid `ANTHROPIC_API_KEY` in the environment.
There is no per-request authentication — deploy behind an API gateway or internal network for production.

## Endpoints

### `GET /health`

Health check. Returns `200 OK` when the service is running.

**Response:**
```json
{"status": "ok", "service": "langchain-document-pipeline"}
```

---

### `POST /ingest/`

Upload and process a PDF document.

**Request:** `multipart/form-data`
- `file`: PDF file (max 50 MB by default)

**Response `200`:**
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "prior_auth_form.pdf",
  "page_count": 12,
  "chunk_count": 47,
  "status": "done"
}
```

**Errors:**
- `400`: Not a PDF or exceeds size limit
- `409`: Document already ingested (same file hash)

---

### `GET /ingest/{document_id}/status`

Poll the ingestion status of a document.

**Response `200`:**
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "prior_auth_form.pdf",
  "status": "done",
  "chunk_count": 47
}
```

**Errors:**
- `404`: Document not found

---

### `GET /documents/`

List all ingested documents, newest first.

**Response `200`:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "prior_auth_form.pdf",
    "page_count": 12,
    "chunk_count": 47,
    "status": "done",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

---

### `GET /documents/{document_id}`

Get full document details including all chunks.

**Response `200`:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "prior_auth_form.pdf",
  "file_hash": "abc123...",
  "page_count": 12,
  "chunk_count": 47,
  "status": "done",
  "error_msg": null,
  "created_at": "2024-01-15T10:30:00Z",
  "chunks": [
    {
      "id": "...",
      "page_number": 3,
      "chunk_index": 0,
      "content": "Full chunk text...",
      "content_preview": "First 200 chars..."
    }
  ]
}
```

**Errors:**
- `400`: Invalid document_id format
- `404`: Document not found

---

### `POST /query/`

Search documents and generate an answer using RAG.

**Request body:**
```json
{
  "question": "What HCPCS codes are ordered for this patient?",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "top_k": 5,
  "threshold": 0.75
}
```

All fields except `question` are optional.

**Response `200`:**
```json
{
  "question": "What HCPCS codes are ordered?",
  "answer": "The following HCPCS codes are ordered: E1390 (oxygen concentrator)...",
  "sources": [
    {
      "chunk_id": "...",
      "document_id": "...",
      "page_number": 3,
      "similarity_score": 0.912,
      "content": "Patient requires E1390 oxygen concentrator..."
    }
  ],
  "model": "claude-3-5-sonnet-20241022",
  "input_tokens": 1247,
  "output_tokens": 89
}
```

---

### `GET /costs/`

Return token usage and cost breakdown.

**Query parameters:**
- `document_id` (optional): Filter by document UUID
- `chain_name` (optional): Filter by chain name (e.g., `hcpcs_extraction`)

**Response `200`:**
```json
{
  "total_cost_usd": 0.042,
  "total_input_tokens": 12450,
  "total_output_tokens": 890,
  "total_cache_write_tokens": 0,
  "total_cache_read_tokens": 0,
  "call_count": 8,
  "by_model": {
    "claude-3-5-sonnet-20241022": {
      "total_cost_usd": 0.042,
      "input_tokens": 12450,
      "output_tokens": 890,
      "calls": 8
    }
  },
  "by_chain": {
    "qa_chain": {"input_tokens": 8200, "output_tokens": 600, "calls": 5},
    "hcpcs_extraction": {"input_tokens": 4250, "output_tokens": 290, "calls": 3}
  }
}
```
