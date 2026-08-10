import httpx
import pytest


@pytest.mark.anyio
async def test_project_crud_preserves_structured_units_and_partial_updates(
    api_client: httpx.AsyncClient,
    api_project_payload: dict[str, object],
) -> None:
    create_response = await api_client.post("/projects", json=api_project_payload)

    assert create_response.status_code == 201
    created = create_response.json()
    project_id = created["id"]
    assert created["lr"]["value"] == pytest.approx(45.0)
    assert created["lr"]["unit"] == "uH"
    assert created["target_efficiency"] == {
        "value": pytest.approx(0.94),
        "unit": "dimensionless",
    }

    list_response = await api_client.get("/projects")
    assert list_response.status_code == 200
    assert [project["id"] for project in list_response.json()["projects"]] == [
        project_id
    ]

    patch_response = await api_client.patch(
        f"/projects/{project_id}",
        json={
            "name": "Updated fixture",
            "lr": {"value": 0.05, "unit": "mH"},
            "primary_switch": {"part_number": "UPDATED-650V"},
        },
    )
    assert patch_response.status_code == 200
    updated = patch_response.json()
    assert updated["name"] == "Updated fixture"
    assert updated["lr"]["value"] == pytest.approx(50.0)
    assert updated["lr"]["unit"] == "uH"
    assert updated["primary_switch"]["manufacturer"] == "Fixture Semiconductor"
    assert updated["primary_switch"]["part_number"] == "UPDATED-650V"

    get_response = await api_client.get(f"/projects/{project_id}")
    assert get_response.status_code == 200
    assert get_response.json() == updated


@pytest.mark.anyio
async def test_project_api_rejects_unknown_project_and_incompatible_units(
    api_client: httpx.AsyncClient,
) -> None:
    missing_response = await api_client.get("/projects/not-present")
    invalid_response = await api_client.post(
        "/projects",
        json={
            "name": "Wrong unit",
            "lr": {"value": 45, "unit": "V"},
        },
    )

    assert missing_response.status_code == 404
    assert invalid_response.status_code == 422
    assert "compatible with H" in invalid_response.json()["detail"]


@pytest.mark.anyio
async def test_project_patch_can_clear_optional_values(
    api_client: httpx.AsyncClient,
    api_project_payload: dict[str, object],
) -> None:
    created = (await api_client.post("/projects", json=api_project_payload)).json()

    response = await api_client.patch(
        f"/projects/{created['id']}",
        json={"lr": None, "primary_switch": None},
    )

    assert response.status_code == 200
    assert response.json()["lr"] is None
    assert response.json()["primary_switch"]["vds_rating"] is None


@pytest.mark.anyio
async def test_project_patch_rejects_null_name(
    api_client: httpx.AsyncClient,
    api_project_payload: dict[str, object],
) -> None:
    created = (await api_client.post("/projects", json=api_project_payload)).json()

    response = await api_client.patch(
        f"/projects/{created['id']}", json={"name": None}
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "name cannot be null"
