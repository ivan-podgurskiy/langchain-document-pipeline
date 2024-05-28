"""SQLAlchemy ORM models for the document pipeline."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class Document(Base):
    """Represents an ingested PDF document."""

    __tablename__ = "documents"

    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename: str = Column(String(512), nullable=False)
    file_hash: str = Column(String(64), nullable=False, unique=True)
    page_count: int = Column(Integer, nullable=False, default=0)
    status: str = Column(
        Enum("pending", "processing", "done", "failed", name="ingestion_status"),
        nullable=False,
        default="pending",
    )
    error_msg: str | None = Column(Text, nullable=True)
    metadata_: dict = Column("metadata", JSONB, nullable=False, default=dict)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now())
    updated_at: datetime = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    chunks: list[Chunk] = relationship(
        "Chunk", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename!r}>"


class Chunk(Base):
    """Represents a text chunk extracted from a document."""

    __tablename__ = "chunks"

    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: uuid.UUID = Column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    content: str = Column(Text, nullable=False)
    page_number: int = Column(Integer, nullable=False, default=0)
    chunk_index: int = Column(Integer, nullable=False, default=0)
    metadata_: dict = Column("metadata", JSONB, nullable=False, default=dict)
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now())

    document: Document = relationship("Document", back_populates="chunks")
    embedding: Embedding = relationship(
        "Embedding", back_populates="chunk", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Chunk id={self.id} page={self.page_number} index={self.chunk_index}>"


class Embedding(Base):
    """Represents a vector embedding for a chunk."""

    __tablename__ = "embeddings"

    id: uuid.UUID = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id: uuid.UUID = Column(
        UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False
    )
    model: str = Column(String(128), nullable=False, default="voyage-large-2")
    created_at: datetime = Column(DateTime(timezone=True), server_default=func.now())

    chunk: Chunk = relationship("Chunk", back_populates="embedding")

    def __repr__(self) -> str:
        return f"<Embedding id={self.id} chunk_id={self.chunk_id} model={self.model!r}>"
