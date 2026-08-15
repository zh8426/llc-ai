from collections.abc import Callable

import numpy as np
import pytest

from app.waveform import (
    ChannelMetadata,
    EdgeDetectionResult,
    SwitchingCycle,
    WaveformAnalysisError,
    WaveformMetadata,
    WaveformSchemaError,
    analyze_waveform_csv,
    calculate_peak,
    calculate_rms,
    calculate_switching_frequency,
    detect_falling_edges,
    detect_rising_edges,
    segment_cycles,
)


def synthetic_gate_signal(
    *,
    frequency: float = 100_000.0,
    sample_rate: float = 10_000_000.0,
    cycle_count: int = 12,
    noise_standard_deviation: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    samples_per_cycle = int(sample_rate / frequency)
    sample_indices = np.arange(samples_per_cycle * cycle_count)
    time = sample_indices.astype(np.float64) / sample_rate
    phase = np.mod(sample_indices, samples_per_cycle) / samples_per_cycle
    gate = np.where((phase >= 0.25) & (phase < 0.75), 12.0, 0.0)
    if noise_standard_deviation:
        gate = gate + np.random.default_rng(42).normal(
            0.0,
            noise_standard_deviation,
            len(gate),
        )
    return time, gate


def test_edges_cycles_and_frequency_match_synthetic_reference() -> None:
    time, gate = synthetic_gate_signal()

    rising = detect_rising_edges(time, gate)
    falling = detect_falling_edges(time, gate)
    cycles = segment_cycles(time, rising)
    frequency = calculate_switching_frequency(cycles)

    assert len(rising.indices) == 12
    assert len(falling.indices) == 12
    assert rising.threshold_source == "automatic"
    assert rising.low_threshold == pytest.approx(3.6)
    assert rising.high_threshold == pytest.approx(8.4)
    assert len(cycles) == 11
    assert all(cycle.duration == pytest.approx(10e-6) for cycle in cycles)
    assert frequency.value == pytest.approx(100_000.0, rel=1e-12)
    assert frequency.unit == "Hz"
    assert frequency.cycle_count == 11
    assert frequency.formula_version == "WAVEFORM-FSW-MEAN-PERIOD-V1"


def test_analysis_pipeline_runs_from_csv_to_structured_features() -> None:
    time, gate = synthetic_gate_signal(cycle_count=4)
    vds = np.where(gate > 6.0, 20.0, 400.0)
    resonant_current = 5.0 * np.sin(2.0 * np.pi * 100_000.0 * time)
    rows = ["time,VGS_Q1,VDS_Q1,IRES"]
    rows.extend(
        f"{timestamp},{vgs},{drain_voltage},{current}"
        for timestamp, vgs, drain_voltage, current in zip(
            time,
            gate,
            vds,
            resonant_current,
            strict=True,
        )
    )
    metadata = WaveformMetadata(
        sample_rate=10_000_000.0,
        channels={
            "VGS_Q1": ChannelMetadata(unit="V"),
            "VDS_Q1": ChannelMetadata(unit="V"),
            "IRES": ChannelMetadata(unit="A"),
        },
        test_condition={"vin": "400 VDC", "load": "500 W"},
    )

    result = analyze_waveform_csv("\n".join(rows), metadata)

    assert result.analysis_version == "WAVEFORM-ANALYSIS-MVP-V1"
    assert result.sample_count == len(time)
    assert result.discarded_samples == 0
    assert len(result.cycles) == 3
    assert result.switching_frequency.value == pytest.approx(100_000.0)
    assert result.channel_features["VDS_Q1"].peak.value == 400.0
    assert result.channel_features["VDS_Q1"].peak.unit == "V"
    assert result.channel_features["IRES"].peak.value == pytest.approx(5.0)
    assert result.channel_features["IRES"].rms.unit == "A"


def test_hysteresis_detects_noisy_gate_edges_without_duplicates() -> None:
    time, gate = synthetic_gate_signal(noise_standard_deviation=0.35)

    assert len(detect_rising_edges(time, gate).indices) == 12
    assert len(detect_falling_edges(time, gate).indices) == 12


def test_explicit_thresholds_are_traceable() -> None:
    time, gate = synthetic_gate_signal(cycle_count=2)

    result = detect_rising_edges(time, gate, low_threshold=2.0, high_threshold=8.0)

    assert result.threshold_source == "explicit"
    assert result.low_threshold == 2.0
    assert result.high_threshold == 8.0


def test_peak_and_sample_rms_match_independent_values() -> None:
    signal = np.array([-3.0, 4.0, -1.0, 0.0], dtype=np.float64)

    peak = calculate_peak(signal, unit="A")
    rms = calculate_rms(signal, unit="A")

    assert peak.value == 4.0
    assert peak.formula_version == "WAVEFORM-ABS-PEAK-V1"
    assert rms.value == pytest.approx(np.sqrt(26.0 / 4.0))
    assert rms.formula_version == "WAVEFORM-RMS-SAMPLE-V1"


def test_time_weighted_rms_supports_irregular_sampling() -> None:
    time = np.array([0.0, 0.1, 0.4, 1.0], dtype=np.float64)
    signal = np.array([0.0, 2.0, 2.0, 0.0], dtype=np.float64)

    result = calculate_rms(signal, unit="A", time=time)

    expected = np.sqrt(np.trapezoid(np.square(signal), time) / (time[-1] - time[0]))
    assert result.value == pytest.approx(expected)
    assert result.formula_version == "WAVEFORM-RMS-TIME-WEIGHTED-V1"


def test_cycle_segmentation_uses_timestamps_for_irregular_samples() -> None:
    time = np.array([0.0, 0.2, 0.5, 1.0, 1.6], dtype=np.float64)
    edges = EdgeDetectionResult(
        direction="rising",
        indices=(1, 3, 4),
        timestamps=(0.2, 1.0, 1.6),
        low_threshold=1.0,
        high_threshold=2.0,
        threshold_source="explicit",
    )

    cycles = segment_cycles(time, edges)

    assert [cycle.duration for cycle in cycles] == pytest.approx([0.8, 0.6])
    assert calculate_switching_frequency(cycles).value == pytest.approx(1.0 / 0.7)


@pytest.mark.parametrize(
    "operation",
    [
        lambda: detect_rising_edges(np.array([0.0]), np.array([0.0])),
        lambda: detect_rising_edges(np.array([0.0, 1.0]), np.array([1.0, 1.0])),
        lambda: calculate_peak(np.array([], dtype=np.float64), unit="A"),
        lambda: calculate_rms(np.array([], dtype=np.float64), unit="A"),
        lambda: calculate_switching_frequency(()),
    ],
)
def test_analysis_rejects_insufficient_data(operation: Callable[[], object]) -> None:
    with pytest.raises(WaveformAnalysisError):
        operation()


@pytest.mark.parametrize(
    "operation",
    [
        lambda: detect_rising_edges(
            np.array([0.0, 1.0]),
            np.array([0.0, np.nan]),
        ),
        lambda: detect_rising_edges(
            np.array([0.0, 1.0]),
            np.array([0.0, 1.0]),
            low_threshold=1.0,
        ),
        lambda: detect_rising_edges(
            np.array([0.0, 1.0]),
            np.array([0.0, 1.0]),
            low_threshold=1.0,
            high_threshold=1.0,
        ),
        lambda: calculate_peak(np.array([1.0, np.inf]), unit="A"),
        lambda: calculate_rms(
            np.array([1.0, 2.0]),
            unit="A",
            time=np.array([1.0, 0.0]),
        ),
        lambda: calculate_switching_frequency(
            (SwitchingCycle(0, 1, 0.0, 0.0, 0.0),)
        ),
    ],
)
def test_analysis_rejects_invalid_data(operation: Callable[[], object]) -> None:
    with pytest.raises(WaveformSchemaError):
        operation()
