"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/documents"
    db_pool_size: int = 10
    db_pool_max_overflow: int = 5

    # Anthropic
    anthropic_api_key: str = ""

    # Voyage AI (embeddings)
    voyage_api_key: str = ""

    # LLM — upgraded to Claude 3.5 Sonnet v2 as default (available Oct 22, 2024)
    llm_model: str = "claude-sonnet-4-6"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.0

    # Embeddings
    # voyage-large-2 produces 1536-dim vectors; voyage-2 produces 1024-dim.
    # Always keep embedding_model and embedding_dimensions in sync.
    embedding_model: str = "voyage-large-2"
    embedding_dimensions: int = 1536  # must match voyage-large-2 output dims

    # Vector store
    vector_similarity_threshold: float = 0.5
    vector_top_k: int = 5

    # Ingestion
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_upload_size_mb: int = 50

    # LangSmith tracing
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "langchain-document-pipeline"

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
