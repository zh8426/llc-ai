from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from app.waveform.exceptions import WaveformSchemaError

ChannelPolarity = Literal[-1, 1]


@dataclass(frozen=True)
class ChannelMetadata:
    """Acquisition metadata required to normalize one physical channel."""

    unit: str
    probe_ratio: float = 1.0
    polarity: ChannelPolarity = 1
    bandwidth_hz: float | None = None

    def __post_init__(self) -> None:
        if not self.unit.strip():
            raise WaveformSchemaError("channel unit must not be empty")
        if not isfinite(self.probe_ratio) or self.probe_ratio <= 0.0:
            raise WaveformSchemaError("probe_ratio must be finite and greater than zero")
        if self.polarity not in (-1, 1):
            raise WaveformSchemaError("channel polarity must be either 1 or -1")
        if self.bandwidth_hz is not None and (
            not isfinite(self.bandwidth_hz) or self.bandwidth_hz <= 0.0
        ):
            raise WaveformSchemaError("bandwidth_hz must be finite and greater than zero")


@dataclass(frozen=True)
class WaveformMetadata:
    """Metadata supplied with a CSV waveform acquisition."""

    sample_rate: float
    channels: Mapping[str, ChannelMetadata]
    test_condition: Mapping[str, str]
    time_unit: str = "s"

    def __post_init__(self) -> None:
        if not isfinite(self.sample_rate) or self.sample_rate <= 0.0:
            raise WaveformSchemaError("sample_rate must be finite and greater than zero")
        if not self.time_unit.strip():
            raise WaveformSchemaError("time_unit must not be empty")
        if not self.test_condition:
            raise WaveformSchemaError("test_condition must not be empty")
        if any(not key.strip() or not value.strip() for key, value in self.test_condition.items()):
            raise WaveformSchemaError("test_condition keys and values must not be empty")
        object.__setattr__(self, "channels", MappingProxyType(dict(self.channels)))
        object.__setattr__(
            self,
            "test_condition",
            MappingProxyType(dict(self.test_condition)),
        )


@dataclass(frozen=True)
class WaveformData:
    """Finite waveform samples normalized to seconds, volts, and amperes."""

    time: NDArray[np.float64]
    channels: Mapping[str, NDArray[np.float64]]
    normalized_channel_units: Mapping[str, str]
    metadata: WaveformMetadata
    discarded_samples: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "channels", MappingProxyType(dict(self.channels)))
        object.__setattr__(
            self,
            "normalized_channel_units",
            MappingProxyType(dict(self.normalized_channel_units)),
        )


@dataclass(frozen=True)
class EdgeDetectionResult:
    direction: Literal["rising", "falling"]
    indices: tuple[int, ...]
    timestamps: tuple[float, ...]
    low_threshold: float
    high_threshold: float
    threshold_source: Literal["automatic", "explicit"]
    algorithm_version: str = "WAVEFORM-SCHMITT-EDGE-V1"


@dataclass(frozen=True)
class SwitchingCycle:
    start_index: int
    end_index: int
    start_time: float
    end_time: float
    duration: float


@dataclass(frozen=True)
class FrequencyMeasurement:
    value: float
    unit: str
    cycle_count: int
    formula_version: str = "WAVEFORM-FSW-MEAN-PERIOD-V1"


@dataclass(frozen=True)
class ScalarWaveformFeature:
    name: str
    value: float
    unit: str
    sample_count: int
    formula_version: str


@dataclass(frozen=True)
class ChannelFeatureSummary:
    peak: ScalarWaveformFeature
    rms: ScalarWaveformFeature


@dataclass(frozen=True)
class WaveformAnalysisResult:
    sample_count: int
    discarded_samples: int
    rising_edges: EdgeDetectionResult
    falling_edges: EdgeDetectionResult
    cycles: tuple[SwitchingCycle, ...]
    switching_frequency: FrequencyMeasurement
    channel_features: Mapping[str, ChannelFeatureSummary]
    analysis_version: str = "WAVEFORM-ANALYSIS-MVP-V1"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "channel_features",
            MappingProxyType(dict(self.channel_features)),
        )
