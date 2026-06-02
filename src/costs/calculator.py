"""Per-model cost calculation for Claude 3 / 3.5 models including prompt caching."""

from __future__ import annotations

from dataclasses import dataclass

# Claude pricing as of October 2024 (USD per 1M tokens)
# Source: https://www.anthropic.com/pricing
MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-3-haiku-20240307": {
        "input": 0.25,
        "output": 1.25,
        "cache_write": 0.30,  # 20% premium over standard input
        "cache_read": 0.03,  # 88% discount from standard input
    },
    "claude-3-sonnet-20240229": {
        "input": 3.00,
        "output": 15.00,
        "cache_write": 3.75,
        "cache_read": 0.30,
    },
    "claude-3-opus-20240229": {
        "input": 15.00,
        "output": 75.00,
        "cache_write": 18.75,
        "cache_read": 1.50,
    },
    "claude-3-5-sonnet-20240620": {
        "input": 3.00,
        "output": 15.00,
        "cache_write": 3.75,
        "cache_read": 0.30,
    },
    "claude-3-5-sonnet-20241022": {
        "input": 3.00,
        "output": 15.00,
        "cache_write": 3.75,
        "cache_read": 0.30,
    },
}

# Fallback pricing for unknown models (conservative estimate)
DEFAULT_PRICING = {
    "input": 3.00,
    "output": 15.00,
    "cache_write": 3.75,
    "cache_read": 0.30,
}


@dataclass
class CostBreakdown:
    """Detailed cost breakdown for a single LLM call."""

    model: str
    input_tokens: int
    output_tokens: int
    cache_write_tokens: int
    cache_read_tokens: int
    input_cost_usd: float
    output_cost_usd: float
    cache_write_cost_usd: float
    cache_read_cost_usd: float

    @property
    def total_cost_usd(self) -> float:
        """Sum of all cost components."""
        return (
            self.input_cost_usd
            + self.output_cost_usd
            + self.cache_write_cost_usd
            + self.cache_read_cost_usd
        )


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_write_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> CostBreakdown:
    """Calculate the USD cost for a single LLM API call.

    Args:
        model: Claude model identifier string.
        input_tokens: Standard (non-cached) input tokens.
        output_tokens: Output/completion tokens.
        cache_write_tokens: Tokens written to the prompt cache.
        cache_read_tokens: Tokens read from the prompt cache.

    Returns:
        CostBreakdown with per-component and total USD costs.
    """
    pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)

    def cost(tokens: int, rate_per_million: float) -> float:
        return (tokens / 1_000_000) * rate_per_million

    return CostBreakdown(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_write_tokens=cache_write_tokens,
        cache_read_tokens=cache_read_tokens,
        input_cost_usd=cost(input_tokens, pricing["input"]),
        output_cost_usd=cost(output_tokens, pricing["output"]),
        cache_write_cost_usd=cost(cache_write_tokens, pricing["cache_write"]),
        cache_read_cost_usd=cost(cache_read_tokens, pricing["cache_read"]),
    )


def aggregate_costs(breakdowns: list[CostBreakdown]) -> dict[str, object]:
    """Aggregate multiple CostBreakdown objects into a summary.

    Args:
        breakdowns: List of per-call cost breakdowns.

    Returns:
        Dict with total_cost_usd, by_model breakdown, and token totals.
    """
    total_cost = sum(b.total_cost_usd for b in breakdowns)
    total_input = sum(b.input_tokens for b in breakdowns)
    total_output = sum(b.output_tokens for b in breakdowns)
    total_cache_write = sum(b.cache_write_tokens for b in breakdowns)
    total_cache_read = sum(b.cache_read_tokens for b in breakdowns)

    by_model: dict[str, dict[str, object]] = {}
    for b in breakdowns:
        if b.model not in by_model:
            by_model[b.model] = {
                "total_cost_usd": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
                "calls": 0,
            }
        entry = by_model[b.model]
        entry["total_cost_usd"] = round(float(entry["total_cost_usd"]) + b.total_cost_usd, 8)
        entry["input_tokens"] = int(entry["input_tokens"]) + b.input_tokens
        entry["output_tokens"] = int(entry["output_tokens"]) + b.output_tokens
        entry["calls"] = int(entry["calls"]) + 1

    return {
        "total_cost_usd": round(total_cost, 6),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cache_write_tokens": total_cache_write,
        "total_cache_read_tokens": total_cache_read,
        "by_model": by_model,
        "call_count": len(breakdowns),
    }
