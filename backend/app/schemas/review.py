from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.engineering import CalculationResult, EngineeringQuantity


class Severity(StrEnum):
    PASS = "PASS"
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class EvidenceSource(StrEnum):
    USER_INPUT = "user_input"
    CALCULATION = "calculation"
    DATASHEET = "datasheet"
    WAVEFORM = "waveform"
    RULE_DEFINITION = "rule_definition"
    VERIFIED_FAULT_CASE = "verified_fault_case"


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: EvidenceSource
    description: str = Field(min_length=1)
    values: dict[str, EngineeringQuantity] = Field(default_factory=dict)
    references: tuple[str, ...] = ()


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str = Field(pattern=r"^LLC-R\d{3}$")
    category: str = Field(min_length=1)
    severity: Severity
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    evidence: tuple[EvidenceItem, ...] = ()
    calculated_values: dict[
        str, CalculationResult | EngineeringQuantity
    ] = Field(default_factory=dict)
    missing_information: tuple[str, ...] = ()
    recommended_action: tuple[str, ...] = ()
    requires_engineer_confirmation: bool
    report_eligible: bool = True


class ReviewSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    pass_count: int = Field(alias="pass", ge=0)
    info: int = Field(ge=0)
    warning: int = Field(ge=0)
    critical: int = Field(ge=0)
    insufficient_data: int = Field(ge=0)


class ReviewParameterName(StrEnum):
    VIN_MIN = "vin_min"
    VIN_NOM = "vin_nom"
    VIN_MAX = "vin_max"
    VOUT = "vout"
    POUT = "pout"
    IOUT = "iout"
    LR = "lr"
    LM = "lm"
    CR = "cr"
    FSW_MIN = "fsw_min"
    FSW_MAX = "fsw_max"
    TRANSFORMER_RATIO = "transformer_ratio"


class LLCProjectReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    vin_min: EngineeringQuantity | None = None
    vin_nom: EngineeringQuantity | None = None
    vin_max: EngineeringQuantity | None = None
    vout: EngineeringQuantity | None = None
    pout: EngineeringQuantity | None = None
    iout: EngineeringQuantity | None = None
    lr: EngineeringQuantity | None = None
    lm: EngineeringQuantity | None = None
    cr: EngineeringQuantity | None = None
    fsw_min: EngineeringQuantity | None = None
    fsw_max: EngineeringQuantity | None = None
    transformer_ratio: EngineeringQuantity | None = None
    dead_time: EngineeringQuantity | None = None


class MOSFETReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    vds_rating: EngineeringQuantity | None = None
    measured_vds_peak: EngineeringQuantity | None = None
    current_rating: EngineeringQuantity | None = None
    measured_peak_current: EngineeringQuantity | None = None
    current_temperature_condition: str | None = Field(default=None, min_length=1)


class ResonantCapacitorReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    voltage_rating: EngineeringQuantity | None = None
    voltage_stress: EngineeringQuantity | None = None
    rms_current_rating: EngineeringQuantity | None = None
    rms_current_stress: EngineeringQuantity | None = None


class ControllerReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    frequency_min: EngineeringQuantity | None = None
    frequency_max: EngineeringQuantity | None = None


class ReviewRequests(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    zvs_analysis_requested: bool = False
    full_gain_review_requested: bool = False


class ReviewSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    output_power_relative_tolerance: float | None = Field(
        default=None,
        ge=0.0,
        allow_inf_nan=False,
    )
    measured_vds_required_margin_ratio: float | None = Field(
        default=None,
        ge=0.0,
        lt=1.0,
        allow_inf_nan=False,
    )
    gain_review_required_parameters: tuple[ReviewParameterName, ...] | None = None


class ReviewContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project: LLCProjectReviewInput = Field(default_factory=LLCProjectReviewInput)
    mosfet: MOSFETReviewInput = Field(default_factory=MOSFETReviewInput)
    resonant_capacitor: ResonantCapacitorReviewInput = Field(
        default_factory=ResonantCapacitorReviewInput
    )
    controller: ControllerReviewInput = Field(default_factory=ControllerReviewInput)
    requests: ReviewRequests = Field(default_factory=ReviewRequests)
    settings: ReviewSettings = Field(default_factory=ReviewSettings)


class ReviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: ReviewSummary
    findings: tuple[Finding, ...]
    excluded_findings: tuple[Finding, ...] = ()

