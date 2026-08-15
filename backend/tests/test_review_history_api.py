import httpx
import pytest


@pytest.mark.anyio
async def test_review_history_requires_project_and_returns_empty_list(
    api_client: httpx.AsyncClient,
) -> None:
    missing = await api_client.get("/projects/not-present/reviews")
    project = (await api_client.post("/projects", json={"name": "No history"})).json()

    response = await api_client.get(f"/projects/{project['id']}/reviews")

    assert missing.status_code == 404
    assert response.status_code == 200
    assert response.json() == {"project_id": project["id"], "reviews": []}


@pytest.mark.anyio
async def test_review_history_reads_immutable_reviews_and_reports_by_id(
    api_client: httpx.AsyncClient,
    api_project_payload: dict[str, object],
) -> None:
    api_project_payload["name"] = "First revision"
    project = (await api_client.post("/projects", json=api_project_payload)).json()
    first = (await api_client.post(f"/projects/{project['id']}/review")).json()
    first_fr = next(
        result["value"]
        for result in first["calculation_snapshot"]["calculations"]
        if result["name"] == "resonant_frequency"
    )

    await api_client.patch(
        f"/projects/{project['id']}",
        json={"name": "Second revision", "lr": {"value": 99, "unit": "uH"}},
    )
    second = (await api_client.post(f"/projects/{project['id']}/review")).json()
    second_fr = next(
        result["value"]
        for result in second["calculation_snapshot"]["calculations"]
        if result["name"] == "resonant_frequency"
    )

    history = await api_client.get(f"/projects/{project['id']}/reviews")
    first_response = await api_client.get(f"/reviews/{first['review_id']}")
    second_response = await api_client.get(f"/reviews/{second['review_id']}")
    latest_response = await api_client.get(f"/projects/{project['id']}/review")
    first_report = await api_client.get(f"/reviews/{first['review_id']}/report")
    second_report = await api_client.get(f"/reviews/{second['review_id']}/report")

    assert history.status_code == 200
    items = history.json()["reviews"]
    assert [item["review_id"] for item in items] == [
        second["review_id"],
        first["review_id"],
    ]
    assert all(item["summary"] for item in items)
    assert all(
        item["calculation_snapshot"]
        == {
            "calculated_at": item["calculation_snapshot"]["calculated_at"],
            "engine_version": "LLC-CALCULATION-ENGINE-V1",
            "calculation_count": 6,
        }
        for item in items
    )
    assert first_response.json() == first
    assert second_response.json() == second
    assert latest_response.json() == second

    assert first_report.status_code == 200
    assert "First revision" in first_report.text
    assert "Second revision" not in first_report.text
    assert format(first_fr, ".8g") in first_report.text
    assert format(second_fr, ".8g") not in first_report.text
    assert second_report.status_code == 200
    assert "Second revision" in second_report.text


@pytest.mark.anyio
async def test_review_id_endpoints_return_not_found(
    api_client: httpx.AsyncClient,
) -> None:
    review = await api_client.get("/reviews/not-present")
    report = await api_client.get("/reviews/not-present/report")

    assert review.status_code == 404
    assert review.json()["detail"] == "Review not found"
    assert report.status_code == 404
    assert report.json()["detail"] == "Review not found"
