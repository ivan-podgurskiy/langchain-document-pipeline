"""POST /extract endpoint: structured HCPCS and demographics extraction."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.config import settings
from src.extraction.entities import HCPCSCode, PatientDemographics
from src.extraction.service import (
    DocumentNotReadyError,
    ExtractionChainName,
    extract_from_document,
)

router = APIRouter(prefix="/extract", tags=["extraction"])


def _default_extract_chains() -> list[ExtractionChainName]:
    return ["hcpcs", "demographics"]


class ExtractRequest(BaseModel):
    """Request body for the /extract endpoint."""

    document_id: str = Field(..., description="UUID of an ingested document")
    chains: list[ExtractionChainName] = Field(
        default_factory=_default_extract_chains,
        min_length=1,
        description="Extraction chains to run: hcpcs, demographics",
    )


class ExtractResponse(BaseModel):
    """Structured extraction result for a document."""

    document_id: str
    hcpcs_codes: list[HCPCSCode]
    patient: PatientDemographics | None
    model: str
    input_tokens: int
    output_tokens: int
    warnings: list[str] = Field(default_factory=list)


@router.post("/", response_model=ExtractResponse)
async def extract_document_entities(request: ExtractRequest) -> ExtractResponse:
    """Run HCPCS and/or demographics extraction on an ingested document.

    Loads all chunk text for the document, runs the selected LangChain extraction
    chains, and returns validated Pydantic entities.

    Raises:
        HTTPException 400: Invalid document_id or missing API key.
        HTTPException 404: Document not found.
        HTTPException 409: Document ingestion not complete.
        HTTPException 422: Document has no extractable text.
    """
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=400,
            detail="ANTHROPIC_API_KEY is not configured",
        )

    try:
        doc_uuid = uuid.UUID(request.document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document_id format")

    unique_chains: list[ExtractionChainName] = []
    for chain in request.chains:
        if chain not in unique_chains:
            unique_chains.append(chain)

    try:
        result, warnings = await extract_from_document(doc_uuid, unique_chains)
    except LookupError:
        raise HTTPException(status_code=404, detail="Document not found")
    except DocumentNotReadyError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"Document is not ready for extraction (status={exc.status})",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return ExtractResponse(
        document_id=result.document_id,
        hcpcs_codes=result.hcpcs_codes,
        patient=result.patient,
        model=result.extraction_model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        warnings=warnings,
    )
