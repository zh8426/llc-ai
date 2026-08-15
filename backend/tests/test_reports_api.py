from datetime import UTC, datetime

import httpx
import pytest

from app.models.review import ReviewProjectSnapshot, ReviewRun
from app.schemas.project import ProjectResponse
from app.services.reports import ReportSnapshotMissingError, render_review_run


@pytest.mark.anyio
async def test_report_requires_project_and_completed_review(
    api_client: httpx.AsyncClient,
) -> None:
    missing_project = await api_client.get("/projects/not-present/report")
    project = (await api_client.post("/projects", json={"name": "No review"})).json()
    missing_review = await api_client.get(f"/projects/{project['id']}/report")

    assert missing_project.status_code == 404
    assert missing_project.json()["code"] == "PROJECT_NOT_FOUND"
    assert missing_review.status_code == 404
    assert missing_review.json()["code"] == "REVIEW_NOT_FOUND"


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
    assert all(
        version in response.text
        for version in (
            "LLC-FR-V1",
            "LLC-FP-V1",
            "LLC-ZR-V1",
            "LLC-LM-LR-RATIO-V1",
            "LLC-IOUT-V1",
            "LLC-PIN-V1",
        )
    )
    assert "LLC-R020" in response.text
    assert "source_type=user_input" in response.text
    assert "human_verified=false" in response.text
    assert "工程说明与免责声明" in response.text
    assert "报告层未重新执行工程计算" in response.text
    assert "输入数据" in response.text
    assert "计算数据" in response.text
    assert "依据" in response.text
    assert "已通过检查" in response.text
    assert "PASS" not in response.text


@pytest.mark.anyio
async def test_report_uses_review_time_project_snapshot_after_project_changes(
    api_client: httpx.AsyncClient,
    api_project_payload: dict[str, object],
) -> None:
    api_project_payload["name"] = "Original review snapshot"
    project = (await api_client.post("/projects", json=api_project_payload)).json()
    original_calculations = (
        await api_client.post(f"/projects/{project['id']}/calculate")
    ).json()["calculations"]
    await api_client.post(f"/projects/{project['id']}/review")
    await api_client.patch(
        f"/projects/{project['id']}",
        json={
            "name": "Changed after review",
            "lr": {"value": 99, "unit": "uH"},
        },
    )
    current_calculations = (
        await api_client.post(f"/projects/{project['id']}/calculate")
    ).json()["calculations"]

    response = await api_client.get(f"/projects/{project['id']}/report")

    assert response.status_code == 200
    assert "Original review snapshot" in response.text
    assert "Changed after review" not in response.text
    assert "99 uH" not in response.text
    original_fr = next(
        result["value"]
        for result in original_calculations
        if result["name"] == "resonant_frequency"
    )
    current_fr = next(
        result["value"]
        for result in current_calculations
        if result["name"] == "resonant_frequency"
    )
    assert format(original_fr, ".8g") in response.text
    assert format(current_fr, ".8g") not in response.text


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


def test_legacy_review_without_calculation_snapshot_requires_new_review_run() -> None:
    now = datetime.now(UTC)
    project = ProjectResponse(
        id="project-id",
        name="Legacy review",
        created_at=now,
        updated_at=now,
    )
    review = ReviewRun(
        project_id=project.id,
        pass_count=0,
        info_count=0,
        warning_count=0,
        critical_count=0,
        insufficient_data_count=0,
    )
    review.project_snapshot = ReviewProjectSnapshot(
        project_data=project.model_dump(mode="json")
    )

    with pytest.raises(ReportSnapshotMissingError, match="Calculation Snapshot"):
        render_review_run(review)
