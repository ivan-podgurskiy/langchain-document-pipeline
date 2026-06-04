"""FastAPI application entry point."""

from __future__ import annotations

import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.api.costs import router as costs_router
from src.api.documents import router as documents_router
from src.api.ingest import router as ingest_router
from src.api.query import router as query_router
from src.config import settings
from src.db.connection import close_pool, get_pool

# Ensure ingest logs are visible
logging.getLogger("src.api.ingest").setLevel(logging.INFO)

# Configure LangSmith tracing if enabled
if settings.langchain_tracing_v2 and settings.langchain_api_key:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project

app = FastAPI(
    title="LangChain Document Pipeline",
    description="RAG pipeline for medical document processing",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Restrict CORS to explicitly configured origins. The wildcard "*" must never be
# combined with allow_credentials=True (browsers reject it and it is a security risk),
# so credentials are only enabled when concrete origins are listed.
_cors_origins = settings.cors_origins_list
_allow_all_origins = "*" in _cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=not _allow_all_origins,
    allow_methods=["GET", "POST", "PUT", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(documents_router)
app.include_router(query_router)
app.include_router(costs_router)

# Dashboard: serve static files; API routes take precedence
_static_dir = Path(__file__).resolve().parent.parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir), html=True), name="static")


@app.on_event("startup")
async def startup() -> None:
    """Initialize database connection pool on application startup."""
    await get_pool()


@app.on_event("shutdown")
async def shutdown() -> None:
    """Close database connection pool on application shutdown."""
    await close_pool()


@app.get("/", include_in_schema=False, response_class=HTMLResponse)
async def dashboard() -> str:
    """Serve dashboard HTML."""
    index_path = Path(__file__).resolve().parent.parent / "static" / "index.html"
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return "<p>Dashboard not found</p>"


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Health check endpoint.

    Returns service status and database connectivity (degraded if DB is down).
    """
    db_status = "ok"
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception:
        db_status = "unavailable"

    overall = "ok" if db_status == "ok" else "degraded"
    return {
        "status": overall,
        "service": "langchain-document-pipeline",
        "database": db_status,
    }


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
    )
