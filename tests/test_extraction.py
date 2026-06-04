"""Tests for extraction models and helpers (no live LLM calls)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from src.extraction.entities import HCPCSCode, ICD10Code, PatientDemographics
from src.extraction.hcpcs_chain import concat_pages, extract_hcpcs_codes


def test_hcpcs_code_normalizes_and_validates() -> None:
    code = HCPCSCode(code="e1390", description="Oxygen concentrator")
    assert code.code == "E1390"


def test_hcpcs_code_rejects_invalid_format() -> None:
    with pytest.raises(ValueError):
        HCPCSCode(code="INVALID", description="bad")


def test_icd10_code_normalizes() -> None:
    dx = ICD10Code(code="j44.1", description="COPD")
    assert dx.code == "J44.1"


def test_patient_full_name() -> None:
    patient = PatientDemographics(first_name="Jane", last_name="Doe")
    assert patient.full_name == "Jane Doe"


def test_concat_pages_adds_markers() -> None:
    text = concat_pages(["Page one text", "Page two text"])
    assert "[PAGE 1]" in text
    assert "[PAGE 2]" in text


def test_extract_hcpcs_codes_parses_llm_json(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "hcpcs_codes": [
            {
                "code": "E1390",
                "description": "Oxygen concentrator",
                "quantity": 1,
                "source_text": "E1390 oxygen concentrator",
            }
        ]
    }
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = MagicMock(content=json.dumps(payload))
    mock_prompt = MagicMock()
    mock_prompt.__or__ = MagicMock(return_value=mock_chain)
    monkeypatch.setattr(
        "src.extraction.hcpcs_chain.ChatPromptTemplate.from_messages",
        lambda *_args, **_kwargs: mock_prompt,
    )

    result = extract_hcpcs_codes("Patient requires E1390 oxygen concentrator.")
    assert len(result["hcpcs_codes"]) == 1
    assert result["hcpcs_codes"][0]["code"] == "E1390"
