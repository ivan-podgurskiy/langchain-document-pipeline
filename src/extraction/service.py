"""Run structured extraction chains against ingested document text."""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from collections.abc import Sequence
from typing import Any, Literal

from pydantic import ValidationError

from src.config import settings
from src.costs.tracker import tracker
from src.db.connection import execute_query
from src.extraction.demographics_chain import extract_demographics
from src.extraction.entities import ExtractionResult, HCPCSCode, PatientDemographics
from src.extraction.hcpcs_chain import concat_pages, extract_hcpcs_codes

ExtractionChainName = Literal["hcpcs", "demographics"]
DEFAULT_CHAINS: tuple[ExtractionChainName, ...] = ("hcpcs", "demographics")


class DocumentNotReadyError(Exception):
    """Raised when a document cannot be extracted yet."""

    def __init__(self, status: str) -> None:
        self.status = status
        super().__init__(f"Document is not ready for extraction (status={status})")


def pages_from_chunks(chunk_rows: Sequence[Any]) -> list[str]:
    """Group chunk rows by page number and join chunk text per page."""
    by_page: dict[int, list[str]] = defaultdict(list)
    for row in chunk_rows:
        by_page[int(row["page_number"])].append(str(row["content"]))
    return ["\n".join(by_page[page]) for page in sorted(by_page)]


async def load_document_for_extraction(
    document_id: uuid.UUID,
) -> tuple[str, list[str]]:
    """Load document metadata and page texts from stored chunks.

    Returns:
        Tuple of (filename, page texts ordered by page number).

    Raises:
        LookupError: Document not found.
        DocumentNotReadyError: Document ingestion not complete.
        ValueError: Document has no chunk text.
    """
    rows = await execute_query(
        """
        SELECT d.filename, d.status
        FROM documents d
        WHERE d.id = $1
        """,
        document_id,
    )
    if not rows:
        raise LookupError("Document not found")

    status = str(rows[0]["status"])
    if status != "done":
        raise DocumentNotReadyError(status)

    chunk_rows = await execute_query(
        """
        SELECT c.page_number, c.content
        FROM chunks c
        WHERE c.document_id = $1
        ORDER BY c.page_number, c.chunk_index
        """,
        document_id,
    )
    if not chunk_rows:
        raise ValueError("Document has no text chunks")

    pages = pages_from_chunks(chunk_rows)
    return str(rows[0]["filename"]), pages


def _parse_hcpcs_codes(raw: dict[str, object], warnings: list[str]) -> list[HCPCSCode]:
    """Validate HCPCS entries from LLM output, skipping invalid rows."""
    codes: list[HCPCSCode] = []
    entries = raw.get("hcpcs_codes")
    if not isinstance(entries, list):
        entries = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        try:
            codes.append(HCPCSCode.model_validate(entry))
        except ValidationError as exc:
            warnings.append(f"Skipped invalid HCPCS entry: {exc.errors()[0]['msg']}")
    if raw.get("parse_error"):
        warnings.append("HCPCS chain returned malformed JSON; partial or empty result")
    return codes


def _parse_patient(raw: dict[str, object], warnings: list[str]) -> PatientDemographics | None:
    """Validate demographics output when required name fields are present."""
    if raw.get("parse_error"):
        warnings.append("Demographics chain returned malformed JSON; patient omitted")
        return None
    if not raw.get("first_name") or not raw.get("last_name"):
        return None
    try:
        return PatientDemographics.model_validate(raw)
    except ValidationError as exc:
        warnings.append(f"Skipped patient demographics: {exc.errors()[0]['msg']}")
        return None


def _run_extraction_sync(
    document_id: str,
    page_texts: list[str],
    chains: list[ExtractionChainName],
) -> tuple[ExtractionResult, list[str]]:
    """Run selected extraction chains synchronously (LLM calls)."""
    warnings: list[str] = []
    input_tokens = 0
    output_tokens = 0
    hcpcs_codes: list[HCPCSCode] = []
    patient: PatientDemographics | None = None
    document_text = concat_pages(page_texts)

    if "hcpcs" in chains:
        raw, usage = extract_hcpcs_codes(page_texts, return_usage=True)
        assert isinstance(raw, dict)
        assert isinstance(usage, dict)
        hcpcs_codes = _parse_hcpcs_codes(raw, warnings)
        input_tokens += int(usage.get("input_tokens", 0))
        output_tokens += int(usage.get("output_tokens", 0))
        tracker.record(
            model=settings.llm_model,
            chain_name="hcpcs_extraction",
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
            document_id=document_id,
        )

    if "demographics" in chains:
        raw_demo, usage = extract_demographics(document_text, return_usage=True)
        assert isinstance(raw_demo, dict)
        assert isinstance(usage, dict)
        patient = _parse_patient(raw_demo, warnings)
        input_tokens += int(usage.get("input_tokens", 0))
        output_tokens += int(usage.get("output_tokens", 0))
        tracker.record(
            model=settings.llm_model,
            chain_name="demographics_extraction",
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
            document_id=document_id,
        )

    return ExtractionResult(
        document_id=document_id,
        hcpcs_codes=hcpcs_codes,
        patient=patient,
        extraction_model=settings.llm_model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    ), warnings


async def extract_from_document(
    document_id: uuid.UUID,
    chains: list[ExtractionChainName] | None = None,
) -> tuple[ExtractionResult, list[str]]:
    """Extract structured entities from an ingested document.

    Args:
        document_id: UUID of the source document.
        chains: Extraction chains to run. Defaults to HCPCS + demographics.

    Returns:
        Tuple of ExtractionResult and non-fatal warning strings.
    """
    selected = chains or list(DEFAULT_CHAINS)
    _, page_texts = await load_document_for_extraction(document_id)

    return await asyncio.to_thread(
        _run_extraction_sync,
        str(document_id),
        page_texts,
        selected,
    )
