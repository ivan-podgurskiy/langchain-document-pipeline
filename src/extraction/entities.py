"""Pydantic v2 models for structured medical document entities."""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class HCPCSCode(BaseModel):
    """A single HCPCS Level II procedure/equipment code."""

    code: str = Field(..., description="HCPCS code, e.g. E1390")
    description: str = Field(..., description="Short description of the code")
    quantity: Optional[float] = Field(None, description="Quantity ordered/prescribed")
    source_text: Optional[str] = Field(None, description="Verbatim text where code appeared")

    @field_validator("code")
    @classmethod
    def validate_hcpcs_format(cls, v: str) -> str:
        """Ensure the code matches HCPCS format: one letter + four digits."""
        v = v.strip().upper()
        if not re.match(r"^[A-Z]\d{4}$", v):
            raise ValueError(f"Invalid HCPCS code format: {v!r}")
        return v


class ICD10Code(BaseModel):
    """An ICD-10-CM diagnosis code."""

    code: str = Field(..., description="ICD-10 code, e.g. J44.1")
    description: str = Field(..., description="Diagnosis description")
    primary: bool = Field(False, description="Whether this is the primary diagnosis")

    @field_validator("code")
    @classmethod
    def normalize_icd10(cls, v: str) -> str:
        """Normalize ICD-10 code to uppercase."""
        return v.strip().upper()


class PatientDemographics(BaseModel):
    """Patient demographic information extracted from intake or referral forms."""

    first_name: str = Field(..., description="Patient first name")
    last_name: str = Field(..., description="Patient last name")
    date_of_birth: Optional[date] = Field(None, description="Date of birth (YYYY-MM-DD)")
    mrn: Optional[str] = Field(None, description="Medical record number")
    insurance_id: Optional[str] = Field(None, description="Primary insurance member ID")
    insurance_name: Optional[str] = Field(None, description="Insurance plan name")
    diagnoses: list[ICD10Code] = Field(default_factory=list, description="Associated diagnoses")

    @property
    def full_name(self) -> str:
        """Return the full name as 'First Last'."""
        return f"{self.first_name} {self.last_name}"


class DiagnosisEntry(BaseModel):
    """A single diagnosis entry from a progress note or assessment."""

    icd10: ICD10Code = Field(..., description="The ICD-10 code and description")
    notes: Optional[str] = Field(None, description="Clinician notes about this diagnosis")
    status: str = Field("active", description="Status: active, resolved, chronic, etc.")


class ExtractionResult(BaseModel):
    """Aggregated result of all extraction chains run on a document."""

    document_id: str = Field(..., description="UUID of the source document")
    hcpcs_codes: list[HCPCSCode] = Field(default_factory=list)
    patient: Optional[PatientDemographics] = None
    diagnoses: list[DiagnosisEntry] = Field(default_factory=list)
    extraction_model: str = Field("claude-3-sonnet-20240229")
    input_tokens: int = Field(0)
    output_tokens: int = Field(0)

    @property
    def total_tokens(self) -> int:
        """Total tokens consumed across all extraction chains."""
        return self.input_tokens + self.output_tokens
