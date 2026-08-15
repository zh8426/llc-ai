import json

import httpx
import pytest


def zvs_csv() -> str:
    rows = ["time,VGS_Q1,VDS_Q1,IRES,VGS_Q2"]
    for index in range(400):
        time = index / 10_000_000.0
        phase = (index % 100) / 100.0
        vgs_q1 = 12.0 if 0.25 <= phase < 0.75 else 0.0
        vgs_q2 = 12.0 if phase >= 0.80 else 0.0
        vds_q1 = 2.0 if 0.25 <= phase < 0.75 else 400.0
        rows.append(f"{time},{vgs_q1},{vds_q1},0,{vgs_q2}")
    return "\n".join(rows)


@pytest.mark.anyio
async def test_waveform_zvs_api_accepts_csv_and_returns_traceable_result(
    api_client: httpx.AsyncClient,
) -> None:
    response = await api_client.post(
        "/waveforms/zvs",
        files={"file": ("fixture.csv", zvs_csv(), "text/csv")},
        data={
            "sample_rate": "10000000",
            "channels": json.dumps(
                {
                    "VGS_Q1": {"unit": "V", "probe_ratio": 1, "polarity": 1},
                    "VDS_Q1": {"unit": "V", "probe_ratio": 1, "polarity": 1},
                    "IRES": {"unit": "A", "probe_ratio": 1, "polarity": 1},
                    "VGS_Q2": {"unit": "V", "probe_ratio": 1, "polarity": 1},
                }
            ),
            "test_condition": json.dumps({"vin": "400 VDC", "load": "500 W"}),
            "vds_zvs_threshold": "10",
            "vds_hard_switching_threshold": "300",
            "gate_low_threshold": "3",
            "gate_high_threshold": "9",
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["zvs_status"] == "LIKELY_ZVS"
    assert result["confidence"] == 1.0
    assert result["switching_frequency"]["value"] == pytest.approx(100_000.0)
    assert result["vds_at_turn_on"]["values"] == pytest.approx([2.0, 2.0, 2.0])
    assert result["dead_time"]["status"] == "AVAILABLE"
    assert result["dead_time"]["values"] == pytest.approx([0.5e-6] * 4)
    assert len(result["gate_turn_on_timestamps"]) == 4
    assert len(result["gate_turn_off_timestamps"]) == 4


@pytest.mark.anyio
async def test_waveform_zvs_api_rejects_invalid_metadata(
    api_client: httpx.AsyncClient,
) -> None:
    response = await api_client.post(
        "/waveforms/zvs",
        files={"file": ("fixture.csv", zvs_csv(), "text/csv")},
        data={
            "sample_rate": "10000000",
            "channels": "not-json",
            "test_condition": json.dumps({"vin": "400 VDC"}),
            "vds_zvs_threshold": "10",
            "vds_hard_switching_threshold": "300",
        },
    )

    assert response.status_code == 422
