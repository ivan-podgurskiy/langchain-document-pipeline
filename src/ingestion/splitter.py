"""Healthcare-aware recursive text splitter for medical documents."""

from __future__ import annotations

from dataclasses import dataclass

from langchain.text_splitter import RecursiveCharacterTextSplitter

from src.ingestion.pdf_loader import DocumentContent, PageContent

# Section headers common in medical/clinical documentation
HEALTHCARE_SEPARATORS = [
    # Major clinical note sections
    "\nASSESSMENT AND PLAN\n",
    "\nASSESSMENT:\n",
    "\nPLAN:\n",
    "\nHISTORY OF PRESENT ILLNESS:\n",
    "\nHPI:\n",
    "\nCHIEF COMPLAINT:\n",
    "\nPAST MEDICAL HISTORY:\n",
    "\nPMH:\n",
    "\nSOCIAL HISTORY:\n",
    "\nFAMILY HISTORY:\n",
    "\nREVIEW OF SYSTEMS:\n",
    "\nROS:\n",
    "\nPHYSICAL EXAMINATION:\n",
    "\nVITAL SIGNS:\n",
    "\nMEDICATIONS:\n",
    "\nALLERGIES:\n",
    "\nDIAGNOSTIC RESULTS:\n",
    "\nLABORATORY:\n",
    "\nIMAGING:\n",
    "\nPROCEDURES:\n",
    # Prior auth / LCD sections
    "\nINDICATION:\n",
    "\nDIAGNOSIS:\n",
    "\nTREATMENT:\n",
    "\nJUSTIFICATION:\n",
    # Generic separators
    "\n\n",
    "\n",
    " ",
    "",
]


@dataclass
class TextChunk:
    """A chunk of text with source metadata."""

    content: str
    page_number: int
    chunk_index: int
    char_count: int
    document_id: str | None = None


def build_splitter(
    chunk_size: int = 1000, chunk_overlap: int = 200
) -> RecursiveCharacterTextSplitter:
    """Build a healthcare-aware recursive character text splitter.

    Uses clinical section headers as primary split points before
    falling back to paragraph and sentence boundaries.

    Args:
        chunk_size: Maximum number of characters per chunk.
        chunk_overlap: Number of overlapping characters between adjacent chunks.

    Returns:
        Configured RecursiveCharacterTextSplitter instance.
    """
    return RecursiveCharacterTextSplitter(
        separators=HEALTHCARE_SEPARATORS,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
    )


MIN_PAGE_CHARS = 10  # Pages with fewer chars are treated as blank/scanned images


def split_document(
    doc: DocumentContent,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[TextChunk]:
    """Split all pages of a document into text chunks.

    Skips pages with fewer than MIN_PAGE_CHARS characters — these are typically
    scanned image pages that contain no extractable text and would produce
    empty or near-empty chunks that degrade retrieval quality.

    Args:
        doc: Loaded document content.
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Overlap between consecutive chunks.

    Returns:
        Ordered list of TextChunk objects across all pages.
    """
    splitter = build_splitter(chunk_size, chunk_overlap)
    all_chunks: list[TextChunk] = []
    chunk_index = 0

    for page in doc.pages:
        if page.char_count < MIN_PAGE_CHARS:
            continue  # skip blank / scanned image pages
        page_chunks = split_page(page, splitter, chunk_index)
        all_chunks.extend(page_chunks)
        chunk_index += len(page_chunks)

    return all_chunks


def split_page(
    page: PageContent,
    splitter: RecursiveCharacterTextSplitter,
    start_index: int = 0,
) -> list[TextChunk]:
    """Split a single page into text chunks.

    Args:
        page: Page content to split.
        splitter: Configured text splitter.
        start_index: Starting chunk_index offset for this page.

    Returns:
        List of TextChunk objects for the page.
    """
    raw_chunks = splitter.split_text(page.text)
    chunks = []
    for i, text in enumerate(raw_chunks):
        chunks.append(
            TextChunk(
                content=text,
                page_number=page.page_number,
                chunk_index=start_index + i,
                char_count=len(text),
            )
        )
    return chunks
