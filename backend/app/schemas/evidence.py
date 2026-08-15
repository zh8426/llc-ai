from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.engineering import EngineeringQuantity


class EvidenceSource(StrEnum):
    USER_INPUT = "user_input"
    CALCULATION = "calculation"
    DATASHEET = "datasheet"
    WAVEFORM = "waveform"
    RULE_DEFINITION = "rule_definition"
    VERIFIED_FAULT_CASE = "verified_fault_case"


class MeasurementSourceType(StrEnum):
    USER_INPUT = "user_input"
    WAVEFORM_DERIVED = "waveform_derived"
    DATASHEET = "datasheet"
    CALCULATED = "calculated"
    IMPORTED = "imported"


class MeasurementEvidence(BaseModel):
    """A quantity plus provenance; it does not imply measurement verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    value: EngineeringQuantity
    source_type: MeasurementSourceType
    source_id: str | None = Field(default=None, min_length=1)
    channel: str | None = Field(default=None, min_length=1)
    test_condition: dict[str, EngineeringQuantity | str] = Field(
        default_factory=dict
    )
    timestamp: datetime | None = None
    human_verified: bool = False

    @model_validator(mode="after")
    def require_waveform_reference(self) -> "MeasurementEvidence":
        if self.source_type == MeasurementSourceType.WAVEFORM_DERIVED:
            if self.source_id is None:
                raise ValueError("waveform-derived evidence requires source_id")
            if self.channel is None:
                raise ValueError("waveform-derived evidence requires channel")
        return self


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: EvidenceSource
    description: str = Field(min_length=1)
    values: dict[str, EngineeringQuantity] = Field(default_factory=dict)
    measurements: dict[str, MeasurementEvidence] = Field(default_factory=dict)
    references: tuple[str, ...] = ()
