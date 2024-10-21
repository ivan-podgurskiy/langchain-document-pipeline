"""Token usage tracking middleware: wraps LLM calls and logs input/output tokens."""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TokenUsageRecord:
    """A single recorded LLM call with token counts."""

    record_id: uuid.UUID
    model: str
    chain_name: str
    document_id: str | None
    input_tokens: int
    output_tokens: int
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def total_tokens(self) -> int:
        """Total tokens for this call."""
        return self.input_tokens + self.output_tokens


class UsageTracker:
    """In-process token usage tracker.

    Stores all LLM call records in memory for aggregation and reporting.
    For production use, records should be flushed to a database periodically.
    """

    def __init__(self) -> None:
        self._records: list[TokenUsageRecord] = []

    def record(
        self,
        model: str,
        chain_name: str,
        input_tokens: int,
        output_tokens: int,
        document_id: str | None = None,
    ) -> TokenUsageRecord:
        """Record token usage for an LLM call.

        Args:
            model: Claude model identifier (e.g. 'claude-3-sonnet-20240229').
            chain_name: Name of the chain (e.g. 'hcpcs_extraction', 'qa_chain').
            input_tokens: Number of input/prompt tokens consumed.
            output_tokens: Number of output/completion tokens generated.
            document_id: Optional UUID string of the associated document.

        Returns:
            The created TokenUsageRecord.
        """
        record = TokenUsageRecord(
            record_id=uuid.uuid4(),
            model=model,
            chain_name=chain_name,
            document_id=document_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        self._records.append(record)
        return record

    def get_all(self) -> list[TokenUsageRecord]:
        """Return all recorded usage entries."""
        return list(self._records)

    def get_by_document(self, document_id: str) -> list[TokenUsageRecord]:
        """Return all usage records for a specific document.

        Args:
            document_id: UUID string of the document to filter by.

        Returns:
            List of matching TokenUsageRecord objects.
        """
        return [r for r in self._records if r.document_id == document_id]

    def get_by_chain(self, chain_name: str) -> list[TokenUsageRecord]:
        """Return all usage records for a specific chain.

        Args:
            chain_name: Name of the chain to filter by.

        Returns:
            List of matching TokenUsageRecord objects.
        """
        return [r for r in self._records if r.chain_name == chain_name]

    def aggregate_by_model(self) -> dict[str, dict[str, int]]:
        """Aggregate total token usage grouped by model.

        Returns:
            Dict mapping model name → {'input_tokens': N, 'output_tokens': N, 'calls': N}.
        """
        result: dict[str, dict[str, int]] = defaultdict(
            lambda: {"input_tokens": 0, "output_tokens": 0, "calls": 0}
        )
        for r in self._records:
            result[r.model]["input_tokens"] += r.input_tokens
            result[r.model]["output_tokens"] += r.output_tokens
            result[r.model]["calls"] += 1
        return dict(result)

    def aggregate_by_chain(self) -> dict[str, dict[str, int]]:
        """Aggregate total token usage grouped by chain name.

        Returns:
            Dict mapping chain name → {'input_tokens': N, 'output_tokens': N, 'calls': N}.
        """
        result: dict[str, dict[str, int]] = defaultdict(
            lambda: {"input_tokens": 0, "output_tokens": 0, "calls": 0}
        )
        for r in self._records:
            result[r.chain_name]["input_tokens"] += r.input_tokens
            result[r.chain_name]["output_tokens"] += r.output_tokens
            result[r.chain_name]["calls"] += 1
        return dict(result)

    def clear(self) -> None:
        """Clear all recorded usage data."""
        self._records.clear()


# Global tracker instance shared across the application
tracker = UsageTracker()
