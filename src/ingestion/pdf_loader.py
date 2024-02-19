"""PDF loading with PyMuPDF: page-level extraction with metadata."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class PageContent:
    """Content extracted from a single PDF page."""

    page_number: int
    text: str
    char_count: int
    metadata: dict = field(default_factory=dict)


@dataclass
class DocumentContent:
    """Full content extracted from a PDF document."""

    filename: str
    file_hash: str
    page_count: int
    pages: list[PageContent]
    metadata: dict = field(default_factory=dict)


def compute_file_hash(path: Path) -> str:
    """Compute SHA-256 hash of a file for deduplication.

    Args:
        path: Path to the file.

    Returns:
        Hex-encoded SHA-256 digest.
    """
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def load_pdf(path: Path | str) -> DocumentContent:
    """Load a PDF and extract text content from each page.

    Uses PyMuPDF (fitz) for robust text extraction including
    support for multi-column layouts and tables.

    Args:
        path: Path to the PDF file.

    Returns:
        DocumentContent with per-page text and metadata.

    Raises:
        FileNotFoundError: If the PDF does not exist.
        fitz.FileDataError: If the file cannot be parsed as a PDF.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    file_hash = compute_file_hash(path)
    pages: list[PageContent] = []

    with fitz.open(str(path)) as doc:
        doc_metadata = {
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "subject": doc.metadata.get("subject", ""),
            "creator": doc.metadata.get("creator", ""),
            "page_count": doc.page_count,
        }

        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            pages.append(
                PageContent(
                    page_number=page_num,
                    text=text,
                    char_count=len(text),
                    metadata={"page_number": page_num},
                )
            )

    return DocumentContent(
        filename=path.name,
        file_hash=file_hash,
        page_count=len(pages),
        pages=pages,
        metadata=doc_metadata,
    )


def load_pdf_bytes(content: bytes, filename: str) -> DocumentContent:
    """Load a PDF from raw bytes (e.g., from an upload).

    Args:
        content: Raw PDF bytes.
        filename: Original filename for metadata.

    Returns:
        DocumentContent with per-page text and metadata.
    """
    file_hash = hashlib.sha256(content).hexdigest()
    pages: list[PageContent] = []

    with fitz.open(stream=content, filetype="pdf") as doc:
        doc_metadata = {
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "page_count": doc.page_count,
        }

        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            pages.append(
                PageContent(
                    page_number=page_num,
                    text=text,
                    char_count=len(text),
                    metadata={"page_number": page_num},
                )
            )

    return DocumentContent(
        filename=filename,
        file_hash=file_hash,
        page_count=len(pages),
        pages=pages,
        metadata=doc_metadata,
    )
