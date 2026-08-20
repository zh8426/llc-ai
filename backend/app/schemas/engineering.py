from datetime import datetime
from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EngineeringQuantity(BaseModel):
    """A scalar engineering value with an explicit unit at a data boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    value: float = Field(allow_inf_nan=False)
    unit: str = Field(min_length=1)

    @field_validator("value", mode="before")
    @classmethod
    def require_numeric_value(cls, value: object) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("value must be a JSON numeric value")
        numeric_value = float(value)
        if not isfinite(numeric_value):
            raise ValueError("value must be finite")
        return numeric_value

    @field_validator("unit")
    @classmethod
    def normalize_unit_text(cls, unit: str) -> str:
        normalized_unit = unit.strip()
        if not normalized_unit:
            raise ValueError("unit must not be empty")
        return normalized_unit


class CalculationResult(BaseModel):
    """Traceable output produced by a deterministic engineering formula."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    value: float = Field(allow_inf_nan=False)
    unit: str = Field(min_length=1)
    inputs: dict[str, EngineeringQuantity]
    formula_version: str = Field(min_length=1)


class ComplexCalculationResult(BaseModel):
    """Traceable output produced by a deterministic complex-valued formula."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    real: float = Field(allow_inf_nan=False)
    imaginary: float = Field(allow_inf_nan=False)
    magnitude: float = Field(ge=0.0, allow_inf_nan=False)
    unit: str = Field(min_length=1)
    inputs: dict[str, EngineeringQuantity]
    formula_version: str = Field(min_length=1)


OperatingRegionValue = Literal["INDUCTIVE", "CAPACITIVE", "BOUNDARY"]


class OperatingRegionResult(BaseModel):
    """Traceable FHA operating-region classification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    operating_region: OperatingRegionValue
    imaginary_impedance: EngineeringQuantity
    input_impedance: ComplexCalculationResult
    formula_version: str = Field(min_length=1)


class OperatingPointCandidate(BaseModel):
    """One numerical FHA root retained as solver evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    switching_frequency: EngineeringQuantity
    normalized_frequency: CalculationResult
    tank_gain: CalculationResult
    operating_region: OperatingRegionValue
    input_impedance: ComplexCalculationResult
    eligible: bool
    rejection_reasons: tuple[str, ...] = ()


class OperatingPointResult(BaseModel):
    """Traceable FHA operating-point result and retained root evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["VALID", "NO_VALID_OPERATING_POINT"]
    model: Literal["FHA"]
    formula_version: str = Field(min_length=1)
    vin: EngineeringQuantity
    load_power: EngineeringQuantity
    equivalent_load: CalculationResult
    required_gain: CalculationResult
    quality_factor: CalculationResult
    candidates: tuple[OperatingPointCandidate, ...]
    switching_frequency: EngineeringQuantity | None = None
    normalized_frequency: CalculationResult | None = None
    tank_gain: CalculationResult | None = None
    operating_region: OperatingRegionValue | None = None
    input_impedance: ComplexCalculationResult | None = None


class OperatingEnvelopePoint(BaseModel):
    """One deterministic point retained for the available inductive FHA peak."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    switching_frequency: EngineeringQuantity
    normalized_frequency: CalculationResult
    tank_gain: CalculationResult
    operating_region: OperatingRegionValue
    input_impedance: ComplexCalculationResult


class OperatingEnvelopeResult(BaseModel):
    """Required-gain targets, available FHA gain, and operating-point envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    formula_version: str = Field(min_length=1)
    frequency_min: EngineeringQuantity
    frequency_max: EngineeringQuantity
    resonant_frequency: CalculationResult
    quality_factor: CalculationResult
    available_gain_max: CalculationResult | None = None
    available_gain_frequency: EngineeringQuantity | None = None
    peak_point: OperatingEnvelopePoint | None = None
    required_gain_at_vin_min: CalculationResult
    required_gain_at_vin_nom: CalculationResult
    required_gain_at_vin_max: CalculationResult
    operating_points: dict[str, OperatingPointResult]


class GainCurvePoint(BaseModel):
    """One traceable point in a deterministic FHA gain curve."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    switching_frequency: EngineeringQuantity
    normalized_frequency: CalculationResult
    tank_gain: CalculationResult
    input_impedance: ComplexCalculationResult
    operating_region: OperatingRegionValue


class GainCurveResult(BaseModel):
    """Frequency sweep of FHA gain with retained impedance evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    formula_version: str = Field(min_length=1)
    frequency_min: EngineeringQuantity
    frequency_max: EngineeringQuantity
    point_count: int = Field(ge=2)
    resonant_frequency: CalculationResult
    equivalent_load: CalculationResult
    quality_factor: CalculationResult
    points: tuple[GainCurvePoint, ...]


class CalculationSnapshot(BaseModel):
    """Immutable output of one canonical project calculation run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str = Field(min_length=1)
    calculated_at: datetime
    engine_version: str = Field(min_length=1)
    calculations: tuple[CalculationResult, ...]
    missing_information: tuple[str, ...] = ()
    errors: dict[str, str] = Field(default_factory=dict)
