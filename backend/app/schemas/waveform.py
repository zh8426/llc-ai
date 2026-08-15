from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ZVSStatusValue = Literal[
    "LIKELY_ZVS",
    "PARTIAL_ZVS",
    "LIKELY_HARD_SWITCHING",
    "INSUFFICIENT_DATA",
]


class WaveformChannelMetadataInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit: str = Field(min_length=1)
    probe_ratio: float = Field(gt=0, allow_inf_nan=False)
    polarity: Literal[-1, 1] = 1
    bandwidth_hz: float | None = Field(default=None, gt=0, allow_inf_nan=False)


class WaveformFrequencyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float = Field(allow_inf_nan=False)
    unit: Literal["Hz"]
    cycle_count: int = Field(ge=1)
    formula_version: str = Field(min_length=1)


class DeadTimeEvidenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_turn_off_time: float = Field(allow_inf_nan=False)
    complementary_turn_on_time: float = Field(allow_inf_nan=False)
    duration: float = Field(gt=0, allow_inf_nan=False)


class DeadTimeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float | None = Field(default=None, allow_inf_nan=False)
    values: tuple[float, ...]
    evidence: tuple[DeadTimeEvidenceResponse, ...]
    valid_cycle_count: int = Field(default=0, ge=0)
    missing_cycle_count: int = Field(default=0, ge=0)
    rejected_cycle_count: int = Field(default=0, ge=0)
    unit: Literal["s"]
    status: Literal["AVAILABLE", "INSUFFICIENT_DATA"]
    formula_version: str = Field(min_length=1)


class VDSAtTurnOnResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float | None = Field(default=None, allow_inf_nan=False)
    values: tuple[float, ...]
    unit: Literal["V"]
    formula_version: str = Field(min_length=1)


class TurnOnEvidenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cycle_index: int = Field(ge=0)
    gate_turn_on_time: float = Field(ge=0, allow_inf_nan=False)
    vds_at_turn_on: float = Field(allow_inf_nan=False)
    ires_at_turn_on: float = Field(allow_inf_nan=False)
    status: ZVSStatusValue


class ZVSAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    switching_frequency: WaveformFrequencyResponse | None
    dead_time: DeadTimeResponse
    vds_at_turn_on: VDSAtTurnOnResponse | None
    zvs_status: ZVSStatusValue
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    evidence_cycles: tuple[TurnOnEvidenceResponse, ...]
    limitations: tuple[str, ...]
    analysis_version: str = Field(min_length=1)
    gate_turn_on_timestamps: tuple[float, ...]
    gate_turn_off_timestamps: tuple[float, ...]
