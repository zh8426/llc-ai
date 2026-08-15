from collections.abc import Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from app.waveform.cycles import segment_cycles
from app.waveform.edges import detect_falling_edges, detect_rising_edges
from app.waveform.exceptions import WaveformAnalysisError, WaveformSchemaError
from app.waveform.features import calculate_switching_frequency
from app.waveform.loader import load_waveform_csv
from app.waveform.models import (
    EdgeDetectionResult,
    FrequencyMeasurement,
    SwitchingCycle,
    WaveformData,
    WaveformMetadata,
)
from app.waveform.preprocessing import require_strictly_increasing_time

ZVSStatus = Literal[
    "LIKELY_ZVS",
    "PARTIAL_ZVS",
    "LIKELY_HARD_SWITCHING",
    "INSUFFICIENT_DATA",
]
DeadTimeStatus = Literal["AVAILABLE", "INSUFFICIENT_DATA"]


@dataclass(frozen=True)
class ZVSAnalyzerConfig:
    """Explicit signal-classification thresholds for one analysis run."""

    vds_zvs_threshold: float
    vds_hard_switching_threshold: float
    gate_low_threshold: float | None = None
    gate_high_threshold: float | None = None

    def __post_init__(self) -> None:
        if not isfinite(self.vds_zvs_threshold) or self.vds_zvs_threshold < 0.0:
            raise WaveformSchemaError("vds_zvs_threshold must be finite and non-negative")
        if (
            not isfinite(self.vds_hard_switching_threshold)
            or self.vds_hard_switching_threshold <= self.vds_zvs_threshold
        ):
            raise WaveformSchemaError(
                "vds_hard_switching_threshold must be finite and greater than the ZVS threshold"
            )
        if (self.gate_low_threshold is None) != (self.gate_high_threshold is None):
            raise WaveformSchemaError(
                "gate_low_threshold and gate_high_threshold must be provided together"
            )


@dataclass(frozen=True)
class TurnOnEvidence:
    cycle_index: int
    gate_turn_on_time: float
    vds_at_turn_on: float
    ires_at_turn_on: float
    status: ZVSStatus


@dataclass(frozen=True)
class DeadTimeEvidence:
    primary_turn_off_time: float
    complementary_turn_on_time: float
    duration: float


@dataclass(frozen=True)
class _DeadTimePairing:
    evidence: tuple[DeadTimeEvidence, ...]
    missing_cycle_count: int
    rejected_cycle_count: int


@dataclass(frozen=True)
class VDSAtTurnOnMeasurement:
    value: float | None
    values: tuple[float, ...]
    unit: str = "V"
    formula_version: str = "WAVEFORM-VDS-TURN-ON-SAMPLE-V1"


@dataclass(frozen=True)
class DeadTimeMeasurement:
    value: float | None
    values: tuple[float, ...]
    evidence: tuple[DeadTimeEvidence, ...] = ()
    valid_cycle_count: int = 0
    missing_cycle_count: int = 0
    rejected_cycle_count: int = 0
    unit: str = "s"
    status: DeadTimeStatus = "INSUFFICIENT_DATA"
    formula_version: str = "WAVEFORM-DEAD-TIME-CYCLE-WINDOW-V2"

    def __post_init__(self) -> None:
        for name, value in (
            ("valid_cycle_count", self.valid_cycle_count),
            ("missing_cycle_count", self.missing_cycle_count),
            ("rejected_cycle_count", self.rejected_cycle_count),
        ):
            if value < 0:
                raise WaveformSchemaError(f"{name} must not be negative")


@dataclass(frozen=True)
class ZVSAnalysisResult:
    switching_frequency: FrequencyMeasurement | None
    dead_time: DeadTimeMeasurement
    vds_at_turn_on: VDSAtTurnOnMeasurement | None
    zvs_status: ZVSStatus
    cycle_consistency: float
    evidence_cycles: tuple[TurnOnEvidence, ...]
    limitations: tuple[str, ...]
    gate_turn_on_timestamps: tuple[float, ...] = ()
    gate_turn_off_timestamps: tuple[float, ...] = ()
    analysis_version: str = "WAVEFORM-ZVS-MVP-V3"

    def __post_init__(self) -> None:
        if not isfinite(self.cycle_consistency) or not 0.0 <= self.cycle_consistency <= 1.0:
            raise WaveformSchemaError(
                "ZVS cycle_consistency must be finite and between zero and one"
            )
        object.__setattr__(self, "limitations", tuple(self.limitations))


def calculate_vds_at_gate_turn_on(
    time: NDArray[np.float64],
    vds: NDArray[np.float64],
    ires: NDArray[np.float64],
    gate_turn_on_edges: EdgeDetectionResult,
) -> VDSAtTurnOnMeasurement:
    """Sample VDS at each detected gate turn-on timestamp without interpolation."""

    _validate_aligned_signals(time, vds, ires)
    if gate_turn_on_edges.direction != "rising":
        raise WaveformSchemaError("VDS turn-on measurement requires rising gate edges")
    values: list[float] = []
    for index in gate_turn_on_edges.indices:
        if index < 0 or index >= len(time):
            raise WaveformSchemaError("gate turn-on index is outside the waveform")
        values.append(float(vds[index]))
    return VDSAtTurnOnMeasurement(
        value=float(np.mean(values)) if values else None,
        values=tuple(values),
    )


def calculate_dead_time(
    primary_turn_off_edges: EdgeDetectionResult,
    complementary_turn_on_edges: EdgeDetectionResult | None,
    *,
    primary_turn_on_edges: EdgeDetectionResult | None = None,
) -> DeadTimeMeasurement:
    """Measure dead time only inside complete primary switching-cycle windows."""

    if primary_turn_off_edges.direction != "falling":
        raise WaveformSchemaError("dead-time measurement requires primary falling edges")
    if primary_turn_on_edges is not None and primary_turn_on_edges.direction != "rising":
        raise WaveformSchemaError("dead-time cycle windows require primary rising edges")
    if complementary_turn_on_edges is None:
        return DeadTimeMeasurement(
            value=None,
            values=(),
            missing_cycle_count=_complete_cycle_count(primary_turn_on_edges),
            status="INSUFFICIENT_DATA",
        )
    if complementary_turn_on_edges.direction != "rising":
        raise WaveformSchemaError("dead-time measurement requires complementary rising edges")

    if primary_turn_on_edges is None:
        return DeadTimeMeasurement(value=None, values=(), status="INSUFFICIENT_DATA")

    pairing = _pair_dead_time_evidence(
        primary_turn_on_edges,
        primary_turn_off_edges,
        complementary_turn_on_edges,
    )
    intervals = tuple(item.duration for item in pairing.evidence)
    if not intervals:
        return DeadTimeMeasurement(
            value=None,
            values=(),
            evidence=(),
            valid_cycle_count=0,
            missing_cycle_count=pairing.missing_cycle_count,
            rejected_cycle_count=pairing.rejected_cycle_count,
            status="INSUFFICIENT_DATA",
        )
    if not np.all(np.isfinite(intervals)) or np.any(np.asarray(intervals) <= 0.0):
        raise WaveformAnalysisError("dead-time intervals must be finite and positive")
    return DeadTimeMeasurement(
        value=float(np.mean(intervals)),
        values=intervals,
        evidence=pairing.evidence,
        valid_cycle_count=len(intervals),
        missing_cycle_count=pairing.missing_cycle_count,
        rejected_cycle_count=pairing.rejected_cycle_count,
        status="AVAILABLE",
    )


def analyze_zvs(
    waveform: WaveformData,
    config: ZVSAnalyzerConfig,
) -> ZVSAnalysisResult:
    """Run deterministic ZVS feature extraction on an already loaded waveform."""

    required = ("VGS_Q1", "VDS_Q1", "IRES")
    missing = tuple(name for name in required if name not in waveform.channels)
    if missing:
        return _insufficient_result(
            f"Missing required waveform channels: {', '.join(missing)}"
        )

    gate = waveform.channels["VGS_Q1"]
    vds = waveform.channels["VDS_Q1"]
    ires = waveform.channels["IRES"]
    rising = detect_rising_edges(
        waveform.time,
        gate,
        low_threshold=config.gate_low_threshold,
        high_threshold=config.gate_high_threshold,
    )
    falling = detect_falling_edges(
        waveform.time,
        gate,
        low_threshold=config.gate_low_threshold,
        high_threshold=config.gate_high_threshold,
    )
    try:
        cycles = segment_cycles(waveform.time, rising)
    except WaveformAnalysisError as error:
        return _insufficient_result(str(error))

    cycle_rising = _edges_for_cycles(waveform.time, cycles, rising)
    vds_measurement = calculate_vds_at_gate_turn_on(
        waveform.time,
        vds,
        ires,
        cycle_rising,
    )
    statuses = tuple(
        _classify_vds(value, config)
        for value in vds_measurement.values
    )
    evidence = tuple(
        TurnOnEvidence(
            cycle_index=index,
            gate_turn_on_time=timestamp,
            vds_at_turn_on=vds_value,
            ires_at_turn_on=float(ires[edge_index]),
            status=status,
        )
        for index, (edge_index, timestamp, vds_value, status) in enumerate(
            zip(
                cycle_rising.indices,
                cycle_rising.timestamps,
                vds_measurement.values,
                statuses,
                strict=True,
            )
        )
    )
    status, cycle_consistency = _summarize_status(statuses)
    complementary_rising = None
    if "VGS_Q2" in waveform.channels:
        complementary_rising = detect_rising_edges(
            waveform.time,
            waveform.channels["VGS_Q2"],
            low_threshold=config.gate_low_threshold,
            high_threshold=config.gate_high_threshold,
        )
    dead_time = calculate_dead_time(
        falling,
        complementary_rising,
        primary_turn_on_edges=rising,
    )
    limitations = [
        "This is a waveform feature classification, not a safety certification or production approval.",
        "Requires qualified engineer review of the original probes, scaling, polarity, and test condition.",
    ]
    if dead_time.status == "INSUFFICIENT_DATA":
        limitations.append(
            "Complementary VGS_Q2 was not available; true half-bridge dead time was not measured."
        )
    elif dead_time.missing_cycle_count or dead_time.rejected_cycle_count:
        limitations.append(
            "Dead-time statistics use only unambiguous cycle windows; "
            f"{dead_time.missing_cycle_count} window(s) were missing and "
            f"{dead_time.rejected_cycle_count} window(s) were rejected."
        )
    return ZVSAnalysisResult(
        switching_frequency=calculate_switching_frequency(cycles),
        dead_time=dead_time,
        vds_at_turn_on=vds_measurement,
        zvs_status=status,
        cycle_consistency=cycle_consistency,
        evidence_cycles=evidence,
        limitations=tuple(limitations),
        gate_turn_on_timestamps=rising.timestamps,
        gate_turn_off_timestamps=falling.timestamps,
    )


def analyze_zvs_csv(
    csv_text: str,
    metadata: WaveformMetadata,
    config: ZVSAnalyzerConfig,
) -> ZVSAnalysisResult:
    return analyze_zvs(load_waveform_csv(csv_text, metadata), config)


def _edges_for_cycles(
    time: NDArray[np.float64],
    cycles: Sequence[SwitchingCycle],
    detected: EdgeDetectionResult,
) -> EdgeDetectionResult:
    indices = tuple(cycle.start_index for cycle in cycles)
    return EdgeDetectionResult(
        direction="rising",
        indices=indices,
        timestamps=tuple(float(time[index]) for index in indices),
        low_threshold=detected.low_threshold,
        high_threshold=detected.high_threshold,
        threshold_source=detected.threshold_source,
    )


def _classify_vds(value: float, config: ZVSAnalyzerConfig) -> ZVSStatus:
    if value <= config.vds_zvs_threshold:
        return "LIKELY_ZVS"
    if value >= config.vds_hard_switching_threshold:
        return "LIKELY_HARD_SWITCHING"
    return "PARTIAL_ZVS"


def _summarize_status(statuses: Sequence[ZVSStatus]) -> tuple[ZVSStatus, float]:
    if not statuses:
        return "INSUFFICIENT_DATA", 0.0
    counts = {status: statuses.count(status) for status in set(statuses)}
    if len(counts) == 1:
        status = statuses[0]
        return status, 1.0
    _, dominant_count = max(counts.items(), key=lambda item: item[1])
    return "PARTIAL_ZVS", dominant_count / len(statuses)


def _pair_dead_time_evidence(
    primary_turn_on_edges: EdgeDetectionResult,
    primary_turn_off_edges: EdgeDetectionResult,
    complementary_turn_on_edges: EdgeDetectionResult,
) -> _DeadTimePairing:
    """Pair edges only when one unambiguous Q2 edge is inside a Q1 cycle window."""

    evidence: list[DeadTimeEvidence] = []
    missing_cycle_count = 0
    rejected_cycle_count = 0
    primary_fall_position = 0
    complementary_rise_position = 0

    for cycle_start, cycle_end in zip(
        primary_turn_on_edges.indices,
        primary_turn_on_edges.indices[1:],
        strict=False,
    ):
        skipped_falls_start = primary_fall_position
        while (
            primary_fall_position < len(primary_turn_off_edges.indices)
            and primary_turn_off_edges.indices[primary_fall_position] <= cycle_start
        ):
            primary_fall_position += 1
        missing_cycle_count += primary_fall_position - skipped_falls_start

        primary_falls_start = primary_fall_position
        while (
            primary_fall_position < len(primary_turn_off_edges.indices)
            and primary_turn_off_edges.indices[primary_fall_position] < cycle_end
        ):
            primary_fall_position += 1
        primary_fall_count = primary_fall_position - primary_falls_start
        if primary_fall_count == 0:
            missing_cycle_count += 1
            continue
        if primary_fall_count > 1:
            rejected_cycle_count += 1
            continue

        fall_position = primary_falls_start
        fall_index = primary_turn_off_edges.indices[fall_position]
        while (
            complementary_rise_position < len(complementary_turn_on_edges.indices)
            and complementary_turn_on_edges.indices[complementary_rise_position] <= fall_index
        ):
            complementary_rise_position += 1
        complementary_rises_start = complementary_rise_position
        while (
            complementary_rise_position < len(complementary_turn_on_edges.indices)
            and complementary_turn_on_edges.indices[complementary_rise_position] < cycle_end
        ):
            complementary_rise_position += 1
        complementary_rise_count = complementary_rise_position - complementary_rises_start
        if complementary_rise_count == 0:
            missing_cycle_count += 1
            continue
        if complementary_rise_count > 1:
            rejected_cycle_count += 1
            continue

        turn_on_position = complementary_rises_start
        turn_off = primary_turn_off_edges.timestamps[fall_position]
        complementary_turn_on = complementary_turn_on_edges.timestamps[turn_on_position]
        evidence.append(
            DeadTimeEvidence(
                primary_turn_off_time=turn_off,
                complementary_turn_on_time=complementary_turn_on,
                duration=float(complementary_turn_on - turn_off),
            )
        )

    missing_cycle_count += len(primary_turn_off_edges.indices) - primary_fall_position
    return _DeadTimePairing(
        evidence=tuple(evidence),
        missing_cycle_count=missing_cycle_count,
        rejected_cycle_count=rejected_cycle_count,
    )


def _complete_cycle_count(primary_turn_on_edges: EdgeDetectionResult | None) -> int:
    if primary_turn_on_edges is None:
        return 0
    return max(len(primary_turn_on_edges.indices) - 1, 0)


def _validate_aligned_signals(
    time: NDArray[np.float64],
    vds: NDArray[np.float64],
    ires: NDArray[np.float64],
) -> None:
    if len(time) != len(vds) or len(time) != len(ires):
        raise WaveformSchemaError("time, VDS, and IRES must have aligned sample counts")
    if len(time) < 2:
        raise WaveformAnalysisError("ZVS analysis requires at least two aligned samples")
    if not np.all(np.isfinite(time)):
        raise WaveformSchemaError("ZVS time samples must be finite")
    if not np.all(np.isfinite(vds)) or not np.all(np.isfinite(ires)):
        raise WaveformSchemaError("ZVS channels must contain finite samples")
    require_strictly_increasing_time(time)


def _insufficient_result(reason: str) -> ZVSAnalysisResult:
    return ZVSAnalysisResult(
        switching_frequency=None,
        dead_time=DeadTimeMeasurement(value=None, values=()),
        vds_at_turn_on=None,
        zvs_status="INSUFFICIENT_DATA",
        cycle_consistency=0.0,
        evidence_cycles=(),
        limitations=(
            reason,
            "Requires qualified engineer review of the original probes, scaling, polarity, and test condition.",
        ),
    )
