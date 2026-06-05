"""Tests for extraction service helpers."""

from __future__ import annotations

from src.extraction.service import pages_from_chunks


def test_pages_from_chunks_groups_by_page() -> None:
    rows = [
        {"page_number": 1, "content": "Line A"},
        {"page_number": 1, "content": "Line B"},
        {"page_number": 2, "content": "Page two"},
    ]
    pages = pages_from_chunks(rows)
    assert pages == ["Line A\nLine B", "Page two"]
