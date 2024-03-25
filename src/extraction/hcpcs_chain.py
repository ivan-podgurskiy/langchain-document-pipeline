"""HCPCS code extraction chain using Claude 3 Sonnet with structured JSON output."""

from __future__ import annotations

import json
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate

from src.config import settings

# System prompt for HCPCS extraction
HCPCS_SYSTEM_PROMPT = """You are a medical billing specialist with expertise in HCPCS Level II codes.
Your task is to extract all HCPCS codes mentioned in the provided clinical documentation.

HCPCS codes follow this format:
- Always start with a letter (A-V)
- Followed by exactly 4 digits
- Examples: E1390, L3020, A4253, K0001, G0008

Return a JSON object with an "hcpcs_codes" array. Each item must have:
- "code": the HCPCS code string (e.g. "E1390")
- "description": short description of what the code represents
- "quantity": numeric quantity if mentioned, null otherwise
- "source_text": the exact text excerpt where the code appeared

Return ONLY valid JSON, no additional text."""

HCPCS_HUMAN_TEMPLATE = """Extract all HCPCS codes from the following medical documentation:

{document_text}

Return the JSON extraction result:"""


def build_hcpcs_chain() -> ChatAnthropic:
    """Build a Claude LLM instance configured for HCPCS extraction.

    Uses claude-3-sonnet-20240229 for structured extraction.

    Returns:
        ChatAnthropic instance with low temperature for deterministic output.
    """
    return ChatAnthropic(
        model="claude-3-sonnet-20240229",
        temperature=0.0,
        max_tokens=2048,
        anthropic_api_key=settings.anthropic_api_key,
    )


def extract_hcpcs_codes(document_text: str, llm: ChatAnthropic | None = None) -> dict[str, Any]:
    """Extract HCPCS codes from clinical documentation.

    Sends the document text to Claude with a structured extraction prompt.
    Returns parsed JSON with extracted codes.

    Args:
        document_text: Raw text of the medical document to process.
        llm: Optional pre-built LLM instance; created fresh if None.

    Returns:
        Dict with "hcpcs_codes" list of extracted code objects.
    """
    if llm is None:
        llm = build_hcpcs_chain()

    prompt = ChatPromptTemplate.from_messages([
        ("system", HCPCS_SYSTEM_PROMPT),
        ("human", HCPCS_HUMAN_TEMPLATE),
    ])

    chain = prompt | llm

    response = chain.invoke({"document_text": document_text})
    content = response.content

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        # Attempt to extract JSON block if wrapped in markdown code fences
        import re
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(1))
        else:
            result = {"hcpcs_codes": [], "parse_error": content[:500]}

    return result
