import httpx
import pytest


@pytest.mark.anyio
async def test_calculate_project_returns_all_six_traceable_results(
    api_client: httpx.AsyncClient,
    api_project_payload: dict[str, object],
) -> None:
    project = (await api_client.post("/projects", json=api_project_payload)).json()

    response = await api_client.post(f"/projects/{project['id']}/calculate")

    assert response.status_code == 200
    body = response.json()
    assert body["missing_information"] == []
    assert body["errors"] == {}
    assert {result["formula_version"] for result in body["calculations"]} == {
        "LLC-FR-V1",
        "LLC-FP-V1",
        "LLC-ZR-V1",
        "LLC-LM-LR-RATIO-V1",
        "LLC-IOUT-V1",
        "LLC-PIN-V1",
    }


@pytest.mark.anyio
async def test_calculate_incomplete_project_returns_missing_information(
    api_client: httpx.AsyncClient,
) -> None:
    project = (await api_client.post("/projects", json={"name": "Incomplete"})).json()

    response = await api_client.post(f"/projects/{project['id']}/calculate")

    assert response.status_code == 200
    assert response.json()["calculations"] == []
    assert set(response.json()["missing_information"]) == {
        "cr",
        "lm",
        "lr",
        "pout",
        "target_efficiency",
        "vout",
    }


@pytest.mark.anyio
async def test_calculate_invalid_project_returns_structured_formula_errors(
    api_client: httpx.AsyncClient,
) -> None:
    project = (
        await api_client.post(
            "/projects",
            json={
                "name": "Invalid values",
                "lr": {"value": -45, "unit": "uH"},
                "lm": {"value": 300, "unit": "uH"},
                "cr": {"value": 47, "unit": "nF"},
            },
        )
    ).json()

    response = await api_client.post(f"/projects/{project['id']}/calculate")

    assert response.status_code == 200
    assert set(response.json()["errors"]) == {
        "characteristic_impedance",
        "inductance_ratio",
        "lower_resonant_frequency",
        "resonant_frequency",
    }
