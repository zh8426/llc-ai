import httpx
import pytest


def verified_fault_case_payload(*, verified: bool) -> dict[str, object]:
    return {
        "symptom": "ZVS lost",
        "observed_features": ["low resonant current at gate turn-on"],
        "root_cause": "Insufficient resonant current at the tested operating point.",
        "verification_steps": [
            "Repeat the measurement with complementary gate and resonant current channels."
        ],
        "fix": ["Review the switching frequency and resonant tank operating point."],
        "waveform_before": "waveform-before-reference",
        "engineer_verified": verified,
    }


@pytest.mark.anyio
async def test_diagnosis_returns_only_verified_cases_and_structured_evidence(
    api_client: httpx.AsyncClient,
    api_project_payload: dict[str, object],
) -> None:
    project_response = await api_client.post("/projects", json=api_project_payload)
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    review_response = await api_client.post(f"/projects/{project_id}/review")
    assert review_response.status_code == 201

    unverified_response = await api_client.post(
        "/fault-cases", json=verified_fault_case_payload(verified=False)
    )
    assert unverified_response.status_code == 201
    verified_response = await api_client.post(
        "/fault-cases", json=verified_fault_case_payload(verified=True)
    )
    assert verified_response.status_code == 201
    verified_case_id = verified_response.json()["case_id"]

    response = await api_client.post(
        "/fault-diagnoses",
        json={
            "project_id": project_id,
            "symptom": "ZVS lost",
            "observed_features": ["low resonant current"],
            "waveform_features": ["zvs_status=PARTIAL_ZVS"],
            "contradicting_features": ["resonant current was not independently verified"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["symptom"] == "ZVS lost"
    assert body["evidence_summary"]["project_id"] == project_id
    assert body["evidence_summary"]["review_id"] == review_response.json()["review_id"]
    assert body["evidence_summary"]["report_eligible_rule_ids"]
    assert len(body["candidate_causes"]) == 1
    candidate = body["candidate_causes"][0]
    assert candidate["source_case_id"] == verified_case_id
    assert candidate["cause"] == (
        "Insufficient resonant current at the tested operating point."
    )
    assert 0 < candidate["confidence"] <= 1
    assert candidate["supporting_evidence"]
    assert candidate["contradicting_evidence"][0]["source"] == "user_input"
    assert candidate["next_measurement"]
    assert candidate["recommended_action"]
    assert "engineer_verified=false" not in response.text


@pytest.mark.anyio
async def test_diagnosis_reports_insufficient_verified_evidence(
    api_client: httpx.AsyncClient,
) -> None:
    project_response = await api_client.post("/projects", json={"name": "Empty diagnosis"})
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    response = await api_client.post(
        "/fault-diagnoses",
        json={"project_id": project_id, "symptom": "MOSFET overheating"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["candidate_causes"] == []
    assert body["evidence_summary"]["verified_case_count"] == 0
    assert any("没有与当前症状匹配" in item for item in body["limitations"])


@pytest.mark.anyio
async def test_diagnosis_requires_existing_project(api_client: httpx.AsyncClient) -> None:
    response = await api_client.post(
        "/fault-diagnoses",
        json={"project_id": "missing-project", "symptom": "ZVS lost"},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "PROJECT_NOT_FOUND"
