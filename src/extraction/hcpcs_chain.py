"""HCPCS code extraction chain with few-shot examples using Claude 3 Sonnet."""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate

from src.config import settings

# System prompt with role and output format
HCPCS_SYSTEM_PROMPT = """You are a medical billing specialist with expertise in HCPCS Level II codes.
Extract ALL HCPCS codes from the clinical documentation provided.

HCPCS code format: one letter (A-V) followed by exactly 4 digits (e.g., E1390, L3020, A4253).

Return a JSON object in this exact format:
{
  "hcpcs_codes": [
    {
      "code": "E1390",
      "description": "Oxygen concentrator, single delivery port",
      "quantity": 1,
      "source_text": "patient requires E1390 oxygen concentrator"
    }
  ]
}

Return ONLY valid JSON. No prose before or after."""

# Five few-shot examples covering common medical equipment scenarios
FEW_SHOT_EXAMPLES = [
    {
        "input": "Patient diagnosed with J44.1 COPD. Ordering E1390 oxygen concentrator, 2 LPM continuous flow. Also require A4216 saline solution 10mL for nebulizer.",
        "output": json.dumps({
            "hcpcs_codes": [
                {"code": "E1390", "description": "Oxygen concentrator, single delivery port", "quantity": 1, "source_text": "E1390 oxygen concentrator"},
                {"code": "A4216", "description": "Saline solution, 10ml", "quantity": None, "source_text": "A4216 saline solution 10mL"},
            ]
        }),
    },
    {
        "input": "Custom molded AFO brace (L1906) fitted for left foot drop secondary to CVA. Diabetic shoes A5500 and inserts A5512 also ordered.",
        "output": json.dumps({
            "hcpcs_codes": [
                {"code": "L1906", "description": "AFO, posterior, custom fabricated", "quantity": 1, "source_text": "AFO brace (L1906)"},
                {"code": "A5500", "description": "Diabetic shoe, custom molded", "quantity": 1, "source_text": "Diabetic shoes A5500"},
                {"code": "A5512", "description": "Inserts, multiple density", "quantity": 1, "source_text": "inserts A5512"},
            ]
        }),
    },
    {
        "input": "Monthly supply: A4253 blood glucose test strips (100ct), A4258 lancets (100ct), B9002 enteral nutrition pump.",
        "output": json.dumps({
            "hcpcs_codes": [
                {"code": "A4253", "description": "Blood glucose test strips, per 50", "quantity": 100, "source_text": "A4253 blood glucose test strips (100ct)"},
                {"code": "A4258", "description": "Lancets, per box of 100", "quantity": 100, "source_text": "A4258 lancets (100ct)"},
                {"code": "B9002", "description": "Enteral nutrition infusion pump", "quantity": 1, "source_text": "B9002 enteral nutrition pump"},
            ]
        }),
    },
    {
        "input": "Standard power wheelchair K0823 with elevating leg rests E0990. Joystick control E2373.",
        "output": json.dumps({
            "hcpcs_codes": [
                {"code": "K0823", "description": "Power wheelchair, group 2 standard", "quantity": 1, "source_text": "power wheelchair K0823"},
                {"code": "E0990", "description": "Wheelchair accessory, elevating leg rest", "quantity": 1, "source_text": "elevating leg rests E0990"},
                {"code": "E2373", "description": "Power wheelchair accessory, joystick", "quantity": 1, "source_text": "Joystick control E2373"},
            ]
        }),
    },
    {
        "input": "No durable medical equipment ordered at this visit. Follow-up in 4 weeks.",
        "output": json.dumps({"hcpcs_codes": []}),
    },
]

HUMAN_TEMPLATE = """Extract all HCPCS codes from the following medical documentation:

{document_text}"""


def build_hcpcs_chain() -> ChatAnthropic:
    """Build a Claude 3 Sonnet LLM for HCPCS extraction.

    Returns:
        ChatAnthropic configured for deterministic structured extraction.
    """
    return ChatAnthropic(
        model="claude-3-sonnet-20240229",
        temperature=0.0,
        max_tokens=2048,
        anthropic_api_key=settings.anthropic_api_key,
    )


def _build_prompt_messages() -> list[tuple[str, str]]:
    """Assemble system + few-shot + human message sequence."""
    messages: list[tuple[str, str]] = [("system", HCPCS_SYSTEM_PROMPT)]
    for example in FEW_SHOT_EXAMPLES:
        messages.append(("human", HUMAN_TEMPLATE.format(document_text=example["input"])))
        messages.append(("assistant", example["output"]))
    messages.append(("human", HUMAN_TEMPLATE))
    return messages


def extract_hcpcs_codes(document_text: str, llm: ChatAnthropic | None = None) -> dict[str, Any]:
    """Extract HCPCS codes from clinical documentation with few-shot prompting.

    Args:
        document_text: Raw clinical text (procedure note, order, etc.).
        llm: Optional pre-built LLM; created fresh if None.

    Returns:
        Dict with "hcpcs_codes" list. Each entry has code, description,
        quantity (nullable), and source_text fields.
    """
    if llm is None:
        llm = build_hcpcs_chain()

    prompt = ChatPromptTemplate.from_messages(_build_prompt_messages())
    chain = prompt | llm
    response = chain.invoke({"document_text": document_text})
    content = str(response.content).strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return {"hcpcs_codes": [], "parse_error": content[:500]}
