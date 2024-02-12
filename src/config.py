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

    # LLM
    llm_model: str = "claude-2.1"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.0

    # Embeddings
    embedding_model: str = "voyage-large-2"
    embedding_dimensions: int = 1536

    # Vector store
    vector_similarity_threshold: float = 0.75
    vector_top_k: int = 5

    # Ingestion
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_upload_size_mb: int = 50

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
