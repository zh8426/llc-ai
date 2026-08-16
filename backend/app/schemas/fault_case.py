from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.engineering import EngineeringQuantity


class FaultSymptom(StrEnum):
    ZVS_LOST = "ZVS lost"
    MOSFET_OVERHEATING = "MOSFET overheating"
    VDS_OVERSHOOT = "VDS overshoot"
    EXCESSIVE_RESONANT_CURRENT = "excessive resonant current"
    STARTUP_FAILURE = "startup failure"
    OUTPUT_UNDERVOLTAGE = "output undervoltage"
    OUTPUT_OSCILLATION = "output oscillation"
    TRANSFORMER_SATURATION_SUSPECTED = "transformer saturation suspected"
    PROTECTION_FALSE_TRIGGERING = "protection false triggering"
    LIGHT_LOAD_INSTABILITY = "light-load instability"


class FaultCaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topology: Literal["Half-Bridge LLC"] = "Half-Bridge LLC"
    power: EngineeringQuantity | None = None
    vin: EngineeringQuantity | None = None
    vout: EngineeringQuantity | None = None
    load: str | None = Field(default=None, max_length=300)
    symptom: FaultSymptom
    observed_features: tuple[str, ...] = Field(min_length=1)
    root_cause: str = Field(min_length=1, max_length=2000)
    verification_steps: tuple[str, ...] = Field(min_length=1)
    fix: tuple[str, ...] = Field(min_length=1)
    waveform_before: str | None = Field(default=None, max_length=2000)
    waveform_after: str | None = Field(default=None, max_length=2000)
    engineer_verified: bool = False
    verification_notes: str | None = Field(default=None, max_length=2000)


class FaultCaseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topology: Literal["Half-Bridge LLC"] | None = None
    power: EngineeringQuantity | None = None
    vin: EngineeringQuantity | None = None
    vout: EngineeringQuantity | None = None
    load: str | None = Field(default=None, max_length=300)
    symptom: FaultSymptom | None = None
    observed_features: tuple[str, ...] | None = Field(default=None, min_length=1)
    root_cause: str | None = Field(default=None, min_length=1, max_length=2000)
    verification_steps: tuple[str, ...] | None = Field(default=None, min_length=1)
    fix: tuple[str, ...] | None = Field(default=None, min_length=1)
    waveform_before: str | None = Field(default=None, max_length=2000)
    waveform_after: str | None = Field(default=None, max_length=2000)
    engineer_verified: bool | None = None
    verification_notes: str | None = Field(default=None, max_length=2000)


class FaultCaseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    topology: Literal["Half-Bridge LLC"]
    power: EngineeringQuantity | None
    vin: EngineeringQuantity | None
    vout: EngineeringQuantity | None
    load: str | None
    symptom: FaultSymptom
    observed_features: tuple[str, ...]
    root_cause: str
    verification_steps: tuple[str, ...]
    fix: tuple[str, ...]
    waveform_before: str | None
    waveform_after: str | None
    engineer_verified: bool
    production_evidence_eligible: bool
    verification_notes: str | None
    similarity_score: float | None = Field(default=None, ge=0, le=1)
    created_at: datetime
    updated_at: datetime


class FaultCaseListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cases: tuple[FaultCaseResponse, ...]
