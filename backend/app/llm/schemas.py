from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class LLMEvidenceSource(StrEnum):
    PROJECT = "project"
    CALCULATION = "calculation"
    DESIGN_REVIEW = "design_review"
    DATASHEET = "datasheet"
    WAVEFORM = "waveform"
    VERIFIED_FAULT_CASE = "verified_fault_case"
    RULE_DEFINITION = "rule_definition"


class LLMEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str = Field(pattern=r"^E\d{3}$")
    source: LLMEvidenceSource
    description: str = Field(min_length=1, max_length=2000)
    references: tuple[str, ...] = Field(min_length=1)


class LLMClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    claim_id: str = Field(pattern=r"^C\d{3}$")
    text: str = Field(min_length=1, max_length=2000)
    evidence_refs: tuple[str, ...] = Field(min_length=1)


class LLMFinalOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: str = Field(min_length=1, max_length=4000)
    claims: tuple[LLMClaim, ...] = Field(max_length=20)
    evidence: tuple[LLMEvidence, ...] = Field(max_length=50)
    missing_information: tuple[str, ...] = Field(max_length=50)
    next_actions: tuple[str, ...] = Field(max_length=20)
    requires_engineer_confirmation: bool


class LLMToolCallRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    arguments: dict[str, object]
    status: str = Field(min_length=1)


class LLMOrchestrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=8000)
    project_id: str | None = Field(default=None, min_length=1, max_length=36)


class LLMOrchestrationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: str
    claims: tuple[LLMClaim, ...]
    evidence: tuple[LLMEvidence, ...]
    missing_information: tuple[str, ...]
    next_actions: tuple[str, ...]
    requires_engineer_confirmation: bool
    tool_calls: tuple[LLMToolCallRecord, ...]
    provider: str
    model: str


class LLMToolCatalogItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    description: str
    parameters: dict[str, object]


class LLMToolCatalogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tools: tuple[LLMToolCatalogItem, ...]
