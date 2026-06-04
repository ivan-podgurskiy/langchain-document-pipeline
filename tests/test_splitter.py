"""Tests for healthcare-aware text splitting."""

from __future__ import annotations

from src.ingestion.pdf_loader import DocumentContent, PageContent
from src.ingestion.splitter import MIN_PAGE_CHARS, build_splitter, split_document, split_page


def test_build_splitter_splits_on_clinical_headers() -> None:
    splitter = build_splitter(chunk_size=500, chunk_overlap=50)
    text = "CHIEF COMPLAINT:\nDyspnea.\n\nASSESSMENT:\nStable on current therapy."
    chunks = splitter.split_text(text)
    assert len(chunks) >= 1


def test_split_document_skips_near_empty_pages() -> None:
    doc = DocumentContent(
        filename="note.pdf",
        file_hash="deadbeef",
        page_count=2,
        pages=[
            PageContent(page_number=1, text="x", char_count=MIN_PAGE_CHARS - 1),
            PageContent(
                page_number=2,
                text="CHIEF COMPLAINT:\nShortness of breath. " * 30,
                char_count=600,
            ),
        ],
    )
    chunks = split_document(doc, chunk_size=200, chunk_overlap=20)
    assert len(chunks) >= 1
    assert all(c.page_number == 2 for c in chunks)


def test_split_page_preserves_chunk_index_offset() -> None:
    page = PageContent(
        page_number=3,
        text="HPI:\n" + ("Follow-up visit. " * 40),
        char_count=400,
    )
    splitter = build_splitter(chunk_size=120, chunk_overlap=10)
    chunks = split_page(page, splitter, start_index=5)
    assert chunks[0].chunk_index == 5
    assert chunks[-1].chunk_index == 5 + len(chunks) - 1
