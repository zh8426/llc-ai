from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.engineering import CalculationSnapshot, EngineeringQuantity
from app.schemas.review import (
    Finding,
    ReviewRequests,
    ReviewSettings,
    ReviewSummary,
)


class LLCCoreProjectInput(BaseModel):
    """Minimum project data required by all Phase 1 core calculations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    lr: EngineeringQuantity
    lm: EngineeringQuantity
    cr: EngineeringQuantity
    vout: EngineeringQuantity
    pout: EngineeringQuantity
    efficiency: EngineeringQuantity


class PrimarySwitchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manufacturer: str | None = Field(default=None, max_length=200)
    part_number: str | None = Field(default=None, max_length=200)
    vds_rating: EngineeringQuantity | None = None
    measured_vds_peak: EngineeringQuantity | None = None
    current_rating: EngineeringQuantity | None = None
    measured_peak_current: EngineeringQuantity | None = None
    current_temperature_condition: str | None = Field(default=None, max_length=500)


class ResonantCapacitorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    voltage_rating: EngineeringQuantity | None = None
    voltage_stress: EngineeringQuantity | None = None
    rms_current_rating: EngineeringQuantity | None = None
    rms_current_stress: EngineeringQuantity | None = None


class ControllerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str | None = Field(default=None, max_length=200)
    frequency_min: EngineeringQuantity | None = None
    frequency_max: EngineeringQuantity | None = None


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    topology: Literal["Half-Bridge LLC"] = "Half-Bridge LLC"
    vin_min: EngineeringQuantity | None = None
    vin_nom: EngineeringQuantity | None = None
    vin_max: EngineeringQuantity | None = None
    vout: EngineeringQuantity | None = None
    iout: EngineeringQuantity | None = None
    pout: EngineeringQuantity | None = None
    target_efficiency: EngineeringQuantity | None = None
    lr: EngineeringQuantity | None = None
    lm: EngineeringQuantity | None = None
    cr: EngineeringQuantity | None = None
    fsw_min: EngineeringQuantity | None = None
    fsw_nom: EngineeringQuantity | None = None
    fsw_max: EngineeringQuantity | None = None
    transformer_ratio: EngineeringQuantity | None = None
    dead_time: EngineeringQuantity | None = None
    rectification_type: Literal["Diode Rectification"] = "Diode Rectification"
    primary_switch: PrimarySwitchInput = Field(default_factory=PrimarySwitchInput)
    resonant_capacitor: ResonantCapacitorInput = Field(
        default_factory=ResonantCapacitorInput
    )
    controller: ControllerInput = Field(default_factory=ControllerInput)
    review_requests: ReviewRequests = Field(default_factory=ReviewRequests)
    review_settings: ReviewSettings = Field(default_factory=ReviewSettings)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, name: str) -> str:
        normalized = name.strip()
        if not normalized:
            raise ValueError("name must not be blank")
        return normalized


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    vin_min: EngineeringQuantity | None = None
    vin_nom: EngineeringQuantity | None = None
    vin_max: EngineeringQuantity | None = None
    vout: EngineeringQuantity | None = None
    iout: EngineeringQuantity | None = None
    pout: EngineeringQuantity | None = None
    target_efficiency: EngineeringQuantity | None = None
    lr: EngineeringQuantity | None = None
    lm: EngineeringQuantity | None = None
    cr: EngineeringQuantity | None = None
    fsw_min: EngineeringQuantity | None = None
    fsw_nom: EngineeringQuantity | None = None
    fsw_max: EngineeringQuantity | None = None
    transformer_ratio: EngineeringQuantity | None = None
    dead_time: EngineeringQuantity | None = None
    primary_switch: PrimarySwitchInput | None = None
    resonant_capacitor: ResonantCapacitorInput | None = None
    controller: ControllerInput | None = None
    review_requests: ReviewRequests | None = None
    review_settings: ReviewSettings | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, name: str | None) -> str | None:
        if name is None:
            return None
        normalized = name.strip()
        if not normalized:
            raise ValueError("name must not be blank")
        return normalized


class ProjectResponse(ProjectCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    projects: tuple[ProjectResponse, ...]


class ProjectCalculationResponse(CalculationSnapshot):
    """API representation of the canonical Calculation Snapshot."""


class ProjectReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    review_id: str
    created_at: datetime
    summary: ReviewSummary
    findings: tuple[Finding, ...]
    excluded_findings: tuple[Finding, ...] = ()
    calculation_snapshot: CalculationSnapshot | None = None
