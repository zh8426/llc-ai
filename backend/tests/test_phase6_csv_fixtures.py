from pathlib import Path

import pytest

from app.waveform import (
    ChannelMetadata,
    WaveformMetadata,
    ZVSAnalyzerConfig,
    analyze_zvs_csv,
)

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "examples" / "waveforms"
CONFIG = ZVSAnalyzerConfig(
    vds_zvs_threshold=10.0,
    vds_hard_switching_threshold=300.0,
    gate_low_threshold=3.0,
    gate_high_threshold=9.0,
)


@pytest.mark.parametrize(
    ("filename", "expected_status", "expected_evidence_statuses"),
    [
        (
            "phase6_likely_zvs.csv",
            "LIKELY_ZVS",
            ("LIKELY_ZVS", "LIKELY_ZVS", "LIKELY_ZVS"),
        ),
        (
            "phase6_partial_zvs.csv",
            "PARTIAL_ZVS",
            ("LIKELY_ZVS", "PARTIAL_ZVS", "LIKELY_HARD_SWITCHING"),
        ),
        (
            "phase6_likely_hard_switching.csv",
            "LIKELY_HARD_SWITCHING",
            ("LIKELY_HARD_SWITCHING",) * 3,
        ),
        ("phase6_insufficient_data.csv", "INSUFFICIENT_DATA", ()),
    ],
)
def test_phase6_classification_fixtures(
    filename: str,
    expected_status: str,
    expected_evidence_statuses: tuple[str, ...],
) -> None:
    result = analyze_zvs_csv(
        (FIXTURE_ROOT / filename).read_text(encoding="utf-8"),
        _metadata(include_q2=False),
        CONFIG,
    )

    assert result.zvs_status == expected_status
    assert tuple(item.status for item in result.evidence_cycles) == expected_evidence_statuses
    if expected_status == "INSUFFICIENT_DATA":
        assert result.switching_frequency is None
        assert result.vds_at_turn_on is None
    else:
        assert result.switching_frequency is not None
        assert result.vds_at_turn_on is not None


@pytest.mark.parametrize(
    ("filename", "valid", "missing", "rejected"),
    [
        ("phase6_dead_time_available.csv", 3, 1, 0),
        ("phase6_dead_time_missing_cycle.csv", 2, 2, 0),
        ("phase6_dead_time_rejected_cycle.csv", 2, 1, 1),
    ],
)
def test_phase6_dead_time_pairing_fixtures(
    filename: str,
    valid: int,
    missing: int,
    rejected: int,
) -> None:
    result = analyze_zvs_csv(
        (FIXTURE_ROOT / filename).read_text(encoding="utf-8"),
        _metadata(include_q2=True),
        CONFIG,
    )

    assert result.dead_time.status == "AVAILABLE"
    assert result.dead_time.value == pytest.approx(1e-6)
    assert result.dead_time.valid_cycle_count == valid
    assert result.dead_time.missing_cycle_count == missing
    assert result.dead_time.rejected_cycle_count == rejected


def test_phase6_scaled_unit_fixture_is_normalized() -> None:
    result = analyze_zvs_csv(
        (FIXTURE_ROOT / "phase6_scaled_units.csv").read_text(encoding="utf-8"),
        WaveformMetadata(
            sample_rate=1_000_000.0,
            time_unit="us",
            channels={
                "VGS_Q1": ChannelMetadata(unit="mV"),
                "VDS_Q1": ChannelMetadata(unit="mV"),
                "IRES": ChannelMetadata(unit="mA"),
            },
            test_condition={"vin": "400 VDC", "load": "500 W"},
        ),
        CONFIG,
    )

    assert result.zvs_status == "LIKELY_ZVS"
    assert result.vds_at_turn_on is not None
    assert result.vds_at_turn_on.value == pytest.approx(2.0)
    assert result.switching_frequency is not None
    assert result.switching_frequency.value == pytest.approx(1.0 / 7e-6)


def _metadata(*, include_q2: bool) -> WaveformMetadata:
    channels = {
        "VGS_Q1": ChannelMetadata(unit="V"),
        "VDS_Q1": ChannelMetadata(unit="V"),
        "IRES": ChannelMetadata(unit="A"),
    }
    if include_q2:
        channels["VGS_Q2"] = ChannelMetadata(unit="V")
    return WaveformMetadata(
        sample_rate=1_000_000.0,
        time_unit="s",
        channels=channels,
        test_condition={"vin": "400 VDC", "load": "500 W"},
    )

