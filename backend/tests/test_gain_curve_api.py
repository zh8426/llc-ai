import httpx
import pytest


@pytest.mark.anyio
async def test_project_gain_curve_api_returns_structured_curve(
    api_client: httpx.AsyncClient,
    api_project_payload: dict[str, object],
) -> None:
    created = (await api_client.post("/projects", json=api_project_payload)).json()

    response = await api_client.post(
        f"/projects/{created['id']}/gain-curve", json={"point_count": 9}
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == created["id"]
    assert payload["formula_version"] == "LLC-GAIN-CURVE-FHA-V1"
    assert payload["point_count"] == 9
    assert len(payload["points"]) == 9
    assert payload["equivalent_load"]["inputs"]["pout"] == {
        "value": pytest.approx(500.0),
        "unit": "W",
    }


@pytest.mark.anyio
async def test_project_gain_curve_api_reports_missing_project_inputs(
    api_client: httpx.AsyncClient,
) -> None:
    created = (await api_client.post("/projects", json={"name": "Incomplete"})).json()

    response = await api_client.post(
        f"/projects/{created['id']}/gain-curve", json={"point_count": 9}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "MISSING_REQUIRED_DATA"
    assert "lr" in response.json()["details"]["missing_information"]


@pytest.mark.anyio
async def test_project_gain_curve_api_rejects_invalid_point_count(
    api_client: httpx.AsyncClient,
    api_project_payload: dict[str, object],
) -> None:
    created = (await api_client.post("/projects", json=api_project_payload)).json()

    response = await api_client.post(
        f"/projects/{created['id']}/gain-curve", json={"point_count": 1002}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_REQUEST"
