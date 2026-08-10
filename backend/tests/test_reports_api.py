import httpx
import pytest

from app.models.review import ReviewRun
from app.services.reports import ReportSnapshotMissingError, render_review_run


@pytest.mark.anyio
async def test_report_requires_project_and_completed_review(
    api_client: httpx.AsyncClient,
) -> None:
    missing_project = await api_client.get("/projects/not-present/report")
    project = (await api_client.post("/projects", json={"name": "No review"})).json()
    missing_review = await api_client.get(f"/projects/{project['id']}/report")

    assert missing_project.status_code == 404
    assert missing_review.status_code == 404


@pytest.mark.anyio
async def test_report_renders_chinese_self_contained_html_from_review_snapshot(
    api_client: httpx.AsyncClient,
    api_project_payload: dict[str, object],
) -> None:
    project = (await api_client.post("/projects", json=api_project_payload)).json()
    await api_client.post(f"/projects/{project['id']}/review")

    response = await api_client.get(f"/projects/{project['id']}/report")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<html lang="zh-CN">' in response.text
    assert "项目信息与设计规格" in response.text
    assert "结构化计算结果" in response.text
    assert "LLC-FR-V1" in response.text
    assert "LLC-R020" in response.text
    assert "Engineering Disclaimer" in response.text
    assert "The reporting layer did not recalculate engineering results." in response.text


@pytest.mark.anyio
async def test_report_uses_review_time_project_snapshot_after_project_changes(
    api_client: httpx.AsyncClient,
    api_project_payload: dict[str, object],
) -> None:
    api_project_payload["name"] = "Original review snapshot"
    project = (await api_client.post("/projects", json=api_project_payload)).json()
    await api_client.post(f"/projects/{project['id']}/review")
    await api_client.patch(
        f"/projects/{project['id']}",
        json={
            "name": "Changed after review",
            "lr": {"value": 99, "unit": "uH"},
        },
    )

    response = await api_client.get(f"/projects/{project['id']}/report")

    assert response.status_code == 200
    assert "Original review snapshot" in response.text
    assert "Changed after review" not in response.text
    assert "99 uH" not in response.text


@pytest.mark.anyio
async def test_report_escapes_user_controlled_project_text(
    api_client: httpx.AsyncClient,
) -> None:
    project = (
        await api_client.post(
            "/projects", json={"name": "<script>alert('unsafe')</script>"}
        )
    ).json()
    await api_client.post(f"/projects/{project['id']}/review")

    response = await api_client.get(f"/projects/{project['id']}/report")

    assert response.status_code == 200
    assert "<script>alert('unsafe')</script>" not in response.text
    assert "&lt;script&gt;alert(&#x27;unsafe&#x27;)&lt;/script&gt;" in response.text


def test_legacy_review_without_snapshot_requires_new_review_run() -> None:
    review = ReviewRun(
        project_id="project-id",
        pass_count=0,
        info_count=0,
        warning_count=0,
        critical_count=0,
        insufficient_data_count=0,
    )

    with pytest.raises(ReportSnapshotMissingError, match="run the project review again"):
        render_review_run(review)
