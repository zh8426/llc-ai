from collections.abc import Callable
from typing import Any

import numpy as np
import pytest

from app.waveform import (
    ChannelMetadata,
    WaveformMetadata,
    WaveformSchemaError,
    WaveformTooLargeError,
    load_waveform_csv,
)


def waveform_metadata(**overrides: Any) -> WaveformMetadata:
    values: dict[str, Any] = {
        "sample_rate": 1_000_000.0,
        "time_unit": "us",
        "channels": {
            "VGS_Q1": ChannelMetadata(unit="mV", probe_ratio=2.0, polarity=1),
            "VDS_Q1": ChannelMetadata(unit="V", probe_ratio=10.0, polarity=-1),
            "IRES": ChannelMetadata(unit="mA", probe_ratio=1.0, polarity=1),
        },
        "test_condition": {"vin": "400 VDC", "load": "500 W"},
    }
    values.update(overrides)
    return WaveformMetadata(**values)


def test_loader_validates_schema_drops_nonfinite_rows_and_normalizes_units() -> None:
    csv_text = """time,VGS_Q1,VDS_Q1,IRES
0,0,-40,1000
1,5000,-39,2000
2,nan,-38,3000
3,5000,-37,4000
"""

    waveform = load_waveform_csv(csv_text, waveform_metadata())

    assert waveform.discarded_samples == 1
    assert waveform.time == pytest.approx(np.array([0.0, 1e-6, 3e-6]))
    assert waveform.channels["VGS_Q1"] == pytest.approx(np.array([0.0, 10.0, 10.0]))
    assert waveform.channels["VDS_Q1"] == pytest.approx(np.array([400.0, 390.0, 370.0]))
    assert waveform.channels["IRES"] == pytest.approx(np.array([1.0, 2.0, 4.0]))
    assert waveform.normalized_channel_units == {
        "VGS_Q1": "V",
        "VDS_Q1": "V",
        "IRES": "A",
    }


@pytest.mark.parametrize("missing", ["time", "VGS_Q1", "VDS_Q1", "IRES"])
def test_loader_rejects_each_missing_required_column(missing: str) -> None:
    columns = [name for name in ("time", "VGS_Q1", "VDS_Q1", "IRES") if name != missing]
    csv_text = ",".join(columns) + "\n" + ",".join("0" for _ in columns) + "\n"

    with pytest.raises(WaveformSchemaError, match="missing required columns"):
        load_waveform_csv(csv_text, waveform_metadata())


def test_loader_rejects_missing_channel_metadata() -> None:
    metadata = waveform_metadata(
        channels={
            "VGS_Q1": ChannelMetadata(unit="V"),
            "VDS_Q1": ChannelMetadata(unit="V"),
        }
    )

    with pytest.raises(WaveformSchemaError, match="missing required channels: IRES"):
        load_waveform_csv("time,VGS_Q1,VDS_Q1,IRES\n0,0,0,0\n", metadata)


def test_loader_rejects_sample_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.waveform.loader.MAX_WAVEFORM_SAMPLES", 2)
    csv_text = "time,VGS_Q1,VDS_Q1,IRES\n0,0,0,0\n1,0,0,0\n2,0,0,0\n"

    with pytest.raises(WaveformTooLargeError, match="WAVEFORM_TOO_LARGE"):
        load_waveform_csv(csv_text, waveform_metadata())


def test_loader_rejects_channel_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.waveform.loader.MAX_WAVEFORM_CHANNELS", 3)
    metadata = waveform_metadata(
        channels={
            "VGS_Q1": ChannelMetadata(unit="V"),
            "VDS_Q1": ChannelMetadata(unit="V"),
            "IRES": ChannelMetadata(unit="A"),
            "VGS_Q2": ChannelMetadata(unit="V"),
        }
    )
    csv_text = "time,VGS_Q1,VDS_Q1,IRES,VGS_Q2\n0,0,0,0,0\n"

    with pytest.raises(WaveformTooLargeError, match="WAVEFORM_TOO_LARGE"):
        load_waveform_csv(csv_text, metadata)


def test_loader_rejects_wrong_channel_unit() -> None:
    metadata = waveform_metadata(
        channels={
            "VGS_Q1": ChannelMetadata(unit="A"),
            "VDS_Q1": ChannelMetadata(unit="V"),
            "IRES": ChannelMetadata(unit="A"),
        }
    )

    with pytest.raises(WaveformSchemaError, match="VGS_Q1 must use a unit compatible with V"):
        load_waveform_csv("time,VGS_Q1,VDS_Q1,IRES\n0,0,0,0\n1,1,1,1\n", metadata)


@pytest.mark.parametrize(
    "vgs_metadata",
    [
        ChannelMetadata(unit="YV"),
        ChannelMetadata(unit="V", probe_ratio=1e308),
    ],
)
def test_loader_rejects_nonfinite_normalized_samples(
    vgs_metadata: ChannelMetadata,
) -> None:
    metadata = waveform_metadata(
        channels={
            "VGS_Q1": vgs_metadata,
            "VDS_Q1": ChannelMetadata(unit="V"),
            "IRES": ChannelMetadata(unit="A"),
        }
    )
    sample = "1e300" if vgs_metadata.unit == "YV" else "2"
    csv_text = f"time,VGS_Q1,VDS_Q1,IRES\n0,{sample},0,0\n1,{sample},0,0\n"

    with pytest.raises(WaveformSchemaError, match="must produce finite samples"):
        load_waveform_csv(csv_text, metadata)


@pytest.mark.parametrize(
    ("csv_text", "message"),
    [
        ("", "header row"),
        ("time,VGS_Q1,VDS_Q1,IRES\n", "sample rows"),
        ("time,VGS_Q1,VDS_Q1,IRES\n0,abc,0,0\n", "must be numeric"),
        ("time,VGS_Q1,VDS_Q1,IRES\n0,0,0,0,extra\n", "extra values"),
        ("time,VGS_Q1,VGS_Q1,VDS_Q1,IRES\n0,0,0,0,0\n", "must be unique"),
        ("time,VGS_Q1,VDS_Q1,IRES\n1,0,0,0\n0,0,0,0\n", "strictly increasing"),
    ],
)
def test_loader_rejects_malformed_csv(csv_text: str, message: str) -> None:
    with pytest.raises(WaveformSchemaError, match=message):
        load_waveform_csv(csv_text, waveform_metadata())


@pytest.mark.parametrize(
    "metadata_factory",
    [
        lambda: waveform_metadata(sample_rate=0.0),
        lambda: waveform_metadata(test_condition={}),
        lambda: waveform_metadata(time_unit=""),
    ],
)
def test_metadata_rejects_missing_or_invalid_required_values(
    metadata_factory: Callable[[], WaveformMetadata],
) -> None:
    with pytest.raises(WaveformSchemaError):
        metadata_factory()


@pytest.mark.parametrize(
    "channel_factory",
    [
        lambda: ChannelMetadata(unit=""),
        lambda: ChannelMetadata(unit="V", probe_ratio=0.0),
        lambda: ChannelMetadata(unit="V", polarity=0),  # type: ignore[arg-type]
        lambda: ChannelMetadata(unit="V", bandwidth_hz=0.0),
    ],
)
def test_channel_metadata_rejects_invalid_values(
    channel_factory: Callable[[], ChannelMetadata],
) -> None:
    with pytest.raises(WaveformSchemaError):
        channel_factory()
