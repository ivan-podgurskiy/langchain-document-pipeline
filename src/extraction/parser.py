"""Output parser with retry logic for malformed JSON responses from LLMs."""

from __future__ import annotations

import json
import re
import time
from typing import Any, Callable

from langchain_anthropic import ChatAnthropic

from src.config import settings

# Maximum temperature to use on final retry attempt
MAX_RETRY_TEMPERATURE = 0.3


class ParseError(Exception):
    """Raised when JSON parsing fails after all retry attempts."""

    pass


def extract_json_from_response(content: str) -> dict[str, Any]:
    """Attempt to extract a JSON object from an LLM response string.

    Tries three strategies in order:
    1. Direct JSON parse of the full content.
    2. Extract JSON from a markdown code block.
    3. Find the first { ... } block via regex.

    Args:
        content: Raw string content from an LLM response.

    Returns:
        Parsed Python dict.

    Raises:
        ValueError: If no valid JSON could be extracted.
    """
    # Strategy 1: direct parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Strategy 2: markdown code fence
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: first balanced brace group
    brace_match = re.search(r"\{.*\}", content, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract JSON from response: {content[:300]!r}")


def parse_with_retry(
    invoke_fn: Callable[[float], str],
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> dict[str, Any]:
    """Parse LLM output with retry logic for malformed JSON.

    On each failure, increases temperature slightly to encourage
    the model to produce output in a different format, then retries.

    Args:
        invoke_fn: Callable that accepts a temperature float and returns
                   the raw LLM response content string.
        max_retries: Maximum number of retry attempts.
        base_delay: Seconds to wait before each retry (multiplied by attempt number).

    Returns:
        Parsed dict from LLM output.

    Raises:
        ParseError: If all retry attempts fail.
    """
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        temperature = min(
            (attempt * 0.1),
            MAX_RETRY_TEMPERATURE,
        )

        try:
            raw_content = invoke_fn(temperature)
            return extract_json_from_response(raw_content)
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < max_retries:
                delay = base_delay * (attempt + 1)
                time.sleep(delay)

    raise ParseError(
        f"Failed to parse LLM output after {max_retries + 1} attempts. Last error: {last_error}"
    )


def build_retry_llm(base_model: str | None = None, temperature: float = 0.0) -> ChatAnthropic:
    """Build a Claude LLM instance with configurable temperature for retry logic.

    Args:
        base_model: Claude model string. Defaults to settings value.
        temperature: Initial temperature.

    Returns:
        ChatAnthropic instance.
    """
    return ChatAnthropic(
        model=base_model or settings.llm_model,
        temperature=temperature,
        max_tokens=settings.llm_max_tokens,
        anthropic_api_key=settings.anthropic_api_key,
    )
