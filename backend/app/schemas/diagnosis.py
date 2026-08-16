from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.fault_case import FaultSymptom


class DiagnosisEvidenceSource(StrEnum):
    USER_INPUT = "user_input"
    PROJECT = "project"
    DESIGN_REVIEW = "design_review"
    WAVEFORM = "waveform"
    VERIFIED_FAULT_CASE = "verified_fault_case"


class DiagnosisEvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: DiagnosisEvidenceSource
    description: str = Field(min_length=1, max_length=1000)
    references: tuple[str, ...] = ()


class FaultDiagnosisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=36)
    symptom: FaultSymptom
    observed_features: tuple[str, ...] = Field(default=(), max_length=50)
    waveform_features: tuple[str, ...] = Field(default=(), max_length=50)
    contradicting_features: tuple[str, ...] = Field(default=(), max_length=50)


class DiagnosisEvidenceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    project_parameter_names: tuple[str, ...]
    review_id: str | None
    report_eligible_rule_ids: tuple[str, ...]
    waveform_feature_names: tuple[str, ...]
    verified_case_count: int = Field(ge=0)


class CandidateCause(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_case_id: str
    cause: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    supporting_evidence: tuple[DiagnosisEvidenceItem, ...]
    contradicting_evidence: tuple[DiagnosisEvidenceItem, ...]
    missing_information: tuple[str, ...]
    next_measurement: tuple[str, ...]
    recommended_action: tuple[str, ...]


class FaultDiagnosisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    symptom: FaultSymptom
    candidate_causes: tuple[CandidateCause, ...]
    evidence_summary: DiagnosisEvidenceSummary
    limitations: tuple[str, ...]
    diagnosis_version: str = "FAULT-DIAGNOSIS-DETERMINISTIC-V1"
