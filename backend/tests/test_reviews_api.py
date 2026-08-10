import httpx
import pytest


@pytest.mark.anyio
async def test_review_api_runs_persists_and_returns_latest_review(
    api_client: httpx.AsyncClient,
    api_project_payload: dict[str, object],
) -> None:
    project = (await api_client.post("/projects", json=api_project_payload)).json()
    project_id = project["id"]

    missing_response = await api_client.get(f"/projects/{project_id}/review")
    run_response = await api_client.post(f"/projects/{project_id}/review")
    latest_response = await api_client.get(f"/projects/{project_id}/review")

    assert missing_response.status_code == 404
    assert run_response.status_code == 201
    review = run_response.json()
    assert review["summary"] == {
        "pass": 13,
        "info": 7,
        "warning": 0,
        "critical": 0,
        "insufficient_data": 0,
    }
    assert [finding["rule_id"] for finding in review["findings"]] == [
        f"LLC-R{number:03d}" for number in range(1, 21)
    ]
    assert latest_response.status_code == 200
    assert latest_response.json() == review


@pytest.mark.anyio
async def test_review_api_exposes_evidence_for_critical_findings(
    api_client: httpx.AsyncClient,
    api_project_payload: dict[str, object],
) -> None:
    api_project_payload["vin_min"] = {"value": 420, "unit": "V"}
    api_project_payload["vin_nom"] = {"value": 360, "unit": "V"}
    api_project_payload["vin_max"] = {"value": 300, "unit": "V"}
    project = (await api_client.post("/projects", json=api_project_payload)).json()

    response = await api_client.post(f"/projects/{project['id']}/review")

    assert response.status_code == 201
    findings = response.json()["findings"]
    critical = [finding for finding in findings if finding["severity"] == "CRITICAL"]
    assert critical
    assert all(finding["evidence"] for finding in critical)
    assert next(
        finding for finding in findings if finding["rule_id"] == "LLC-R003"
    )["severity"] == "CRITICAL"


@pytest.mark.anyio
async def test_review_api_reports_incomplete_project_without_guessing_values(
    api_client: httpx.AsyncClient,
) -> None:
    project = (await api_client.post("/projects", json={"name": "Incomplete"})).json()

    response = await api_client.post(f"/projects/{project['id']}/review")

    assert response.status_code == 201
    review = response.json()
    assert review["summary"]["insufficient_data"] > 0
    assert all(
        finding["severity"] != "WARNING" or finding["evidence"]
        for finding in review["findings"]
    )
