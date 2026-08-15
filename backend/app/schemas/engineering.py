from datetime import datetime
from math import isfinite

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


class CalculationSnapshot(BaseModel):
    """Immutable output of one canonical project calculation run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str = Field(min_length=1)
    calculated_at: datetime
    engine_version: str = Field(min_length=1)
    calculations: tuple[CalculationResult, ...]
    missing_information: tuple[str, ...] = ()
    errors: dict[str, str] = Field(default_factory=dict)
