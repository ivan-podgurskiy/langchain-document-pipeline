"""Patient demographics extraction chain: name, DOB, MRN, insurance, ICD-10 codes."""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate

from src.config import settings

DEMOGRAPHICS_SYSTEM_PROMPT = """You are a healthcare data analyst specializing in patient intake
and referral form processing. Extract structured patient demographic information from the text.

Return a JSON object with this structure:
{
  "first_name": "string",
  "last_name": "string",
  "date_of_birth": "YYYY-MM-DD or null",
  "mrn": "string or null",
  "insurance_id": "string or null",
  "insurance_name": "string or null",
  "diagnoses": [
    {
      "code": "ICD-10 code",
      "description": "diagnosis description",
      "primary": true/false
    }
  ]
}

Rules:
- Use null for fields not found in the document
- Date of birth must be ISO format (YYYY-MM-DD)
- ICD-10 codes: letter + digits + optional dot + digits (e.g., J44.1, E11.65)
- Return ONLY valid JSON"""

FEW_SHOT_EXAMPLES = [
    {
        "input": """PATIENT INTAKE FORM
Patient: Margaret Sullivan
DOB: 03/14/1958  MRN: 1047382
Insurance: BlueCross BlueShield  ID: XYZ9912234
Primary Diagnosis: J44.1 - Chronic obstructive pulmonary disease, exacerbation
Secondary: E11.65 - Type 2 diabetes with hyperglycemia""",
        "output": json.dumps({
            "first_name": "Margaret",
            "last_name": "Sullivan",
            "date_of_birth": "1958-03-14",
            "mrn": "1047382",
            "insurance_id": "XYZ9912234",
            "insurance_name": "BlueCross BlueShield",
            "diagnoses": [
                {"code": "J44.1", "description": "Chronic obstructive pulmonary disease, exacerbation", "primary": True},
                {"code": "E11.65", "description": "Type 2 diabetes with hyperglycemia", "primary": False},
            ],
        }),
    },
    {
        "input": """Referral for physical therapy.
Patient: Robert Chen, born January 5 1972.
MRN not on file. Aetna insurance, member #AE5678901.
Diagnosis: M54.5 low back pain (primary), M51.16 disc degeneration lumbar (secondary).""",
        "output": json.dumps({
            "first_name": "Robert",
            "last_name": "Chen",
            "date_of_birth": "1972-01-05",
            "mrn": None,
            "insurance_id": "AE5678901",
            "insurance_name": "Aetna",
            "diagnoses": [
                {"code": "M54.5", "description": "low back pain", "primary": True},
                {"code": "M51.16", "description": "disc degeneration lumbar", "primary": False},
            ],
        }),
    },
    {
        "input": """Progress note - no intake form available. Patient presents for follow-up.
No insurance information on file. No MRN assigned yet.""",
        "output": json.dumps({
            "first_name": None,
            "last_name": None,
            "date_of_birth": None,
            "mrn": None,
            "insurance_id": None,
            "insurance_name": None,
            "diagnoses": [],
        }),
    },
]

HUMAN_TEMPLATE = """Extract patient demographics from the following document:

{document_text}"""


def build_demographics_chain() -> ChatAnthropic:
    """Build a Claude 3 Sonnet LLM for demographics extraction.

    Returns:
        ChatAnthropic configured with zero temperature for deterministic output.
    """
    return ChatAnthropic(
        model="claude-3-sonnet-20240229",
        temperature=0.0,
        max_tokens=1024,
        anthropic_api_key=settings.anthropic_api_key,
    )


def extract_demographics(document_text: str, llm: ChatAnthropic | None = None) -> dict[str, Any]:
    """Extract patient demographics from a medical document.

    Uses Claude 3 Sonnet with few-shot examples to parse patient name,
    date of birth, MRN, insurance information, and ICD-10 diagnoses.

    Args:
        document_text: Raw text of the medical document (intake form, referral, etc.).
        llm: Optional pre-built LLM; created fresh if None.

    Returns:
        Dict with patient demographic fields. Missing fields are null.
    """
    if llm is None:
        llm = build_demographics_chain()

    messages: list[tuple[str, str]] = [("system", DEMOGRAPHICS_SYSTEM_PROMPT)]
    for example in FEW_SHOT_EXAMPLES:
        messages.append(("human", HUMAN_TEMPLATE.format(document_text=example["input"])))
        messages.append(("assistant", example["output"]))
    messages.append(("human", HUMAN_TEMPLATE))

    prompt = ChatPromptTemplate.from_messages(messages)
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
        return {
            "first_name": None, "last_name": None, "date_of_birth": None,
            "mrn": None, "insurance_id": None, "insurance_name": None,
            "diagnoses": [], "parse_error": content[:300],
        }
