from collections.abc import Callable
from typing import Literal

import numpy as np
import pytest

from app.waveform import (
    ChannelMetadata,
    EdgeDetectionResult,
    SwitchingCycle,
    WaveformAnalysisError,
    WaveformData,
    WaveformMetadata,
    WaveformSchemaError,
    ZVSAnalyzerConfig,
    analyze_waveform_csv,
    analyze_zvs,
    analyze_zvs_csv,
    calculate_dead_time,
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


def zvs_csv_fixture(
    *,
    vds_turn_on_values: tuple[float, ...],
    include_complementary_gate: bool = False,
) -> tuple[str, WaveformMetadata]:
    time, gate = synthetic_gate_signal(cycle_count=4)
    samples_per_cycle = 100
    vds = np.full(len(time), 400.0)
    for cycle_index, turn_on_value in enumerate(vds_turn_on_values):
        start = cycle_index * samples_per_cycle + 25
        end = min(start + 50, len(vds))
        vds[start:end] = turn_on_value
    ires = 5.0 * np.sin(2.0 * np.pi * 100_000.0 * time)
    columns = ["time", "VGS_Q1", "VDS_Q1", "IRES"]
    q2 = np.where(
        (np.mod(np.arange(len(time)), samples_per_cycle) >= 80),
        12.0,
        0.0,
    )
    if include_complementary_gate:
        columns.append("VGS_Q2")
    rows = [",".join(columns)]
    for index, (timestamp, vgs, drain_voltage, current) in enumerate(
        zip(time, gate, vds, ires, strict=True)
    ):
        values = [timestamp, vgs, drain_voltage, current]
        if include_complementary_gate:
            values.append(q2[index])
        rows.append(",".join(str(value) for value in values))
    channels = {
        "VGS_Q1": ChannelMetadata(unit="V"),
        "VDS_Q1": ChannelMetadata(unit="V"),
        "IRES": ChannelMetadata(unit="A"),
    }
    if include_complementary_gate:
        channels["VGS_Q2"] = ChannelMetadata(unit="V")
    metadata = WaveformMetadata(
        sample_rate=10_000_000.0,
        channels=channels,
        test_condition={"vin": "400 VDC", "load": "500 W"},
    )
    return "\n".join(rows), metadata


def zvs_config() -> ZVSAnalyzerConfig:
    return ZVSAnalyzerConfig(
        vds_zvs_threshold=10.0,
        vds_hard_switching_threshold=300.0,
        gate_low_threshold=3.0,
        gate_high_threshold=9.0,
    )


def explicit_edges(
    direction: Literal["rising", "falling"], indices: tuple[int, ...]
) -> EdgeDetectionResult:
    return EdgeDetectionResult(
        direction=direction,
        indices=indices,
        timestamps=tuple(index * 1e-6 for index in indices),
        low_threshold=3.0,
        high_threshold=9.0,
        threshold_source="explicit",
    )


def test_zvs_analysis_classifies_clean_zvs_with_cycle_evidence() -> None:
    csv_text, metadata = zvs_csv_fixture(vds_turn_on_values=(2.0, 2.0, 2.0))

    result = analyze_zvs_csv(csv_text, metadata, zvs_config())

    assert result.zvs_status == "LIKELY_ZVS"
    assert result.analysis_version == "WAVEFORM-ZVS-MVP-V2"
    assert result.confidence == 1.0
    assert result.switching_frequency is not None
    assert result.switching_frequency.value == pytest.approx(100_000.0)
    assert result.vds_at_turn_on is not None
    assert result.vds_at_turn_on.values == pytest.approx((2.0, 2.0, 2.0))
    assert len(result.evidence_cycles) == 3
    assert all(evidence.status == "LIKELY_ZVS" for evidence in result.evidence_cycles)
    assert result.dead_time.status == "INSUFFICIENT_DATA"
    assert any("true half-bridge dead time" in limitation for limitation in result.limitations)


def test_zvs_analysis_classifies_partial_and_hard_switching() -> None:
    partial_csv, metadata = zvs_csv_fixture(vds_turn_on_values=(2.0, 100.0, 400.0))
    hard_csv, _ = zvs_csv_fixture(vds_turn_on_values=(400.0, 400.0, 400.0))

    partial = analyze_zvs_csv(partial_csv, metadata, zvs_config())
    hard = analyze_zvs_csv(hard_csv, metadata, zvs_config())

    assert partial.zvs_status == "PARTIAL_ZVS"
    assert partial.confidence == pytest.approx(1.0 / 3.0)
    assert [evidence.status for evidence in partial.evidence_cycles] == [
        "LIKELY_ZVS",
        "PARTIAL_ZVS",
        "LIKELY_HARD_SWITCHING",
    ]
    assert hard.zvs_status == "LIKELY_HARD_SWITCHING"
    assert hard.confidence == 1.0


def test_dead_time_is_available_only_with_complementary_gate_edges() -> None:
    csv_text, metadata = zvs_csv_fixture(
        vds_turn_on_values=(2.0, 2.0, 2.0),
        include_complementary_gate=True,
    )

    result = analyze_zvs_csv(csv_text, metadata, zvs_config())

    assert result.dead_time.status == "AVAILABLE"
    assert result.dead_time.value == pytest.approx(0.5e-6)
    assert result.dead_time.values == pytest.approx((0.5e-6,) * 3)
    assert result.dead_time.valid_cycle_count == 3
    assert result.dead_time.missing_cycle_count == 1
    assert result.dead_time.rejected_cycle_count == 0
    assert result.dead_time.formula_version == "WAVEFORM-DEAD-TIME-CYCLE-WINDOW-V2"


def test_dead_time_does_not_pair_across_a_missing_cycle() -> None:
    primary_rising = explicit_edges("rising", (0, 100, 200, 300, 400))
    primary_falling = explicit_edges("falling", (75, 175, 275, 375))
    complementary_rising = explicit_edges("rising", (80, 280))

    result = calculate_dead_time(
        primary_falling,
        complementary_rising,
        primary_turn_on_edges=primary_rising,
    )

    assert result.status == "AVAILABLE"
    assert result.values == pytest.approx((5e-6, 5e-6))
    assert result.valid_cycle_count == 2
    assert result.missing_cycle_count == 2
    assert result.rejected_cycle_count == 0
    assert [item.complementary_turn_on_time for item in result.evidence] == pytest.approx(
        (80e-6, 280e-6)
    )


def test_dead_time_rejects_multiple_complementary_edges_in_one_cycle() -> None:
    primary_rising = explicit_edges("rising", (0, 100, 200, 300, 400))
    primary_falling = explicit_edges("falling", (75, 175, 275, 375))
    complementary_rising = explicit_edges("rising", (80, 90, 180, 280))

    result = calculate_dead_time(
        primary_falling,
        complementary_rising,
        primary_turn_on_edges=primary_rising,
    )

    assert result.status == "AVAILABLE"
    assert result.values == pytest.approx((5e-6, 5e-6))
    assert result.valid_cycle_count == 2
    assert result.missing_cycle_count == 1
    assert result.rejected_cycle_count == 1


def test_dead_time_without_complementary_gate_is_explicitly_insufficient() -> None:
    falling = detect_falling_edges(
        np.array([0.0, 1.0, 2.0]),
        np.array([2.0, 0.0, 0.0]),
        low_threshold=1.0,
        high_threshold=1.5,
    )

    result = calculate_dead_time(falling, None)

    assert result.status == "INSUFFICIENT_DATA"
    assert result.value is None
    assert result.values == ()


def test_zvs_analysis_returns_insufficient_data_for_missing_channels() -> None:
    time = np.array([0.0, 1.0], dtype=np.float64)
    metadata = WaveformMetadata(
        sample_rate=1.0,
        channels={"VGS_Q1": ChannelMetadata(unit="V")},
        test_condition={"vin": "400 VDC"},
    )
    waveform = WaveformData(
        time=time,
        channels={"VGS_Q1": np.array([0.0, 12.0])},
        normalized_channel_units={"VGS_Q1": "V"},
        metadata=metadata,
    )

    result = analyze_zvs(waveform, zvs_config())

    assert result.zvs_status == "INSUFFICIENT_DATA"
    assert result.confidence == 0.0
    assert result.vds_at_turn_on is None


@pytest.mark.parametrize(
    "config_factory",
    [
        lambda: ZVSAnalyzerConfig(
            vds_zvs_threshold=-1.0,
            vds_hard_switching_threshold=300.0,
        ),
        lambda: ZVSAnalyzerConfig(
            vds_zvs_threshold=300.0,
            vds_hard_switching_threshold=10.0,
        ),
        lambda: ZVSAnalyzerConfig(
            vds_zvs_threshold=10.0,
            vds_hard_switching_threshold=300.0,
            gate_low_threshold=3.0,
        ),
    ],
)
def test_zvs_config_rejects_invalid_thresholds(
    config_factory: Callable[[], ZVSAnalyzerConfig],
) -> None:
    with pytest.raises(WaveformSchemaError):
        config_factory()


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
