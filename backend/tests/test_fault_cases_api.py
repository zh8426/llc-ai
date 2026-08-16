import httpx
import pytest


def fault_case_payload() -> dict[str, object]:
    return {
        "power": {"value": 500, "unit": "W"},
        "vin": {"value": 400, "unit": "V"},
        "vout": {"value": 48, "unit": "V"},
        "load": "500 W electronic load",
        "symptom": "ZVS lost",
        "observed_features": ["VDS remains high at gate turn-on"],
        "root_cause": "Insufficient resonant current at the tested operating point.",
        "verification_steps": ["Repeat the measurement with VGS_Q2 and IRES captured."],
        "fix": ["Review switching frequency and resonant tank operating point."],
        "waveform_before": "waveform-before-reference",
        "waveform_after": "waveform-after-reference",
        "verification_notes": "Fixture data reviewed by the power engineer.",
    }


@pytest.mark.anyio
async def test_fault_case_crud_and_verified_filter(
    api_client: httpx.AsyncClient,
) -> None:
    create_response = await api_client.post("/fault-cases", json=fault_case_payload())

    assert create_response.status_code == 201
    case = create_response.json()
    case_id = case["case_id"]
    assert case["power"] == {"value": 500.0, "unit": "W"}
    assert case["engineer_verified"] is False
    assert case["production_evidence_eligible"] is False

    search_response = await api_client.get("/fault-cases", params={"query": "ZVS"})
    assert search_response.status_code == 200
    search_results = search_response.json()["cases"]
    assert len(search_results) == 1
    assert search_results[0]["case_id"] == case_id
    assert search_results[0]["similarity_score"] > 0

    verified_only = await api_client.get(
        "/fault-cases", params={"engineer_verified": "true"}
    )
    assert verified_only.json()["cases"] == []

    update_response = await api_client.patch(
        f"/fault-cases/{case_id}",
        json={"engineer_verified": True},
    )
    assert update_response.status_code == 200
    assert update_response.json()["engineer_verified"] is True
    assert update_response.json()["production_evidence_eligible"] is True

    verified_only = await api_client.get(
        "/fault-cases", params={"engineer_verified": "true"}
    )
    assert [item["case_id"] for item in verified_only.json()["cases"]] == [case_id]

    delete_response = await api_client.delete(f"/fault-cases/{case_id}")
    assert delete_response.status_code == 204
    missing_response = await api_client.get(f"/fault-cases/{case_id}")
    assert missing_response.status_code == 404
    assert missing_response.json()["code"] == "FAULT_CASE_NOT_FOUND"


@pytest.mark.anyio
async def test_fault_case_rejects_incompatible_engineering_unit(
    api_client: httpx.AsyncClient,
) -> None:
    payload = fault_case_payload()
    payload["power"] = {"value": 500, "unit": "V"}

    response = await api_client.post("/fault-cases", json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_ENGINEERING_UNIT"
    assert "detail" not in response.json()


@pytest.mark.anyio
async def test_fault_case_validation_requires_structured_evidence_fields(
    api_client: httpx.AsyncClient,
) -> None:
    response = await api_client.post(
        "/fault-cases",
        json={"symptom": "ZVS lost", "root_cause": "Incomplete fixture"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_REQUEST"
