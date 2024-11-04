"""GET /costs endpoint: token usage and cost breakdown by document and chain."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.costs.calculator import CostBreakdown, aggregate_costs, calculate_cost
from src.costs.tracker import tracker

router = APIRouter(prefix="/costs", tags=["costs"])


class ModelCostSummary(BaseModel):
    """Cost and token summary for a single model."""

    total_cost_usd: float
    input_tokens: int
    output_tokens: int
    calls: int


class CostResponse(BaseModel):
    """Response body for the /costs endpoint."""

    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    total_cache_write_tokens: int
    total_cache_read_tokens: int
    call_count: int
    by_model: dict[str, ModelCostSummary]
    by_chain: dict[str, dict[str, object]]


class ChainCostSummary(BaseModel):
    """Cost and token summary for a single chain."""

    input_tokens: int
    output_tokens: int
    calls: int


@router.get("/", response_model=CostResponse)
async def get_costs(
    document_id: Optional[str] = Query(None, description="Filter by document UUID"),
    chain_name: Optional[str] = Query(None, description="Filter by chain name"),
) -> CostResponse:
    """Return token usage and cost breakdown.

    Supports optional filtering by document ID or chain name.
    Costs are computed dynamically from the in-memory usage tracker.

    Args:
        document_id: Optional UUID string to filter records by document.
        chain_name: Optional chain name to filter records.

    Returns:
        CostResponse with total costs and breakdowns by model and chain.
    """
    records = tracker.get_all()

    if document_id:
        records = [r for r in records if r.document_id == document_id]
    if chain_name:
        records = [r for r in records if r.chain_name == chain_name]

    breakdowns: list[CostBreakdown] = [
        calculate_cost(
            model=r.model,
            input_tokens=r.input_tokens,
            output_tokens=r.output_tokens,
        )
        for r in records
    ]

    summary = aggregate_costs(breakdowns)

    by_model_response = {
        model: ModelCostSummary(**data)  # type: ignore[arg-type]
        for model, data in summary["by_model"].items()
    }

    by_chain = tracker.aggregate_by_chain()
    if chain_name:
        by_chain = {k: v for k, v in by_chain.items() if k == chain_name}

    return CostResponse(
        total_cost_usd=summary["total_cost_usd"],
        total_input_tokens=summary["total_input_tokens"],
        total_output_tokens=summary["total_output_tokens"],
        total_cache_write_tokens=summary["total_cache_write_tokens"],
        total_cache_read_tokens=summary["total_cache_read_tokens"],
        call_count=summary["call_count"],
        by_model=by_model_response,
        by_chain=by_chain,
    )
