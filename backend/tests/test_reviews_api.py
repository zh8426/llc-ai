import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.review import ReviewFinding
from app.schemas.review import Finding, ReviewResult, ReviewSummary, Severity
from app.services import reviews as review_service


@pytest.mark.anyio
async def test_review_api_runs_persists_and_returns_latest_review(
    api_client: httpx.AsyncClient,
    api_project_payload: dict[str, object],
    monkeypatch,
) -> None:
    calculation_calls = 0
    canonical_calculation = review_service.calculate_project

    def tracked_calculation(project):
        nonlocal calculation_calls
        calculation_calls += 1
        return canonical_calculation(project)

    monkeypatch.setattr(review_service, "calculate_project", tracked_calculation)
    project = (await api_client.post("/projects", json=api_project_payload)).json()
    project_id = project["id"]

    missing_response = await api_client.get(f"/projects/{project_id}/review")
    run_response = await api_client.post(f"/projects/{project_id}/review")
    latest_response = await api_client.get(f"/projects/{project_id}/review")

    assert missing_response.status_code == 404
    assert run_response.status_code == 201
    review = run_response.json()
    assert calculation_calls == 1
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
    calculation_snapshot = review["calculation_snapshot"]
    assert calculation_snapshot["engine_version"] == "LLC-CALCULATION-ENGINE-V1"
    assert len(calculation_snapshot["calculations"]) == 6
    assert {result["formula_version"] for result in calculation_snapshot["calculations"]} == {
        "LLC-FR-V1",
        "LLC-FP-V1",
        "LLC-ZR-V1",
        "LLC-LM-LR-RATIO-V1",
        "LLC-IOUT-V1",
        "LLC-PIN-V1",
    }
    r012 = next(finding for finding in review["findings"] if finding["rule_id"] == "LLC-R012")
    measured_vds = r012["evidence"][0]["measurements"]["measured_vds_peak"]
    assert measured_vds["source_type"] == "user_input"
    assert measured_vds["human_verified"] is False
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
    assert review["calculation_snapshot"]["calculations"] == []
    assert set(review["calculation_snapshot"]["missing_information"]) == {
        "cr",
        "lm",
        "lr",
        "pout",
        "target_efficiency",
        "vout",
    }
    assert all(
        finding["severity"] != "WARNING" or finding["evidence"]
        for finding in review["findings"]
    )


@pytest.mark.anyio
async def test_review_persists_and_exposes_excluded_findings_without_reporting_them(
    api_client: httpx.AsyncClient,
    api_session_factory: sessionmaker[Session],
    api_project_payload: dict[str, object],
    monkeypatch,
) -> None:
    excluded = Finding(
        rule_id="LLC-R999",
        category="Audit fixture",
        severity=Severity.WARNING,
        title="Unsupported warning must remain auditable",
        description="This warning has no evidence and must not enter the report.",
        requires_engineer_confirmation=True,
        report_eligible=False,
    )
    gate = Finding(
        rule_id="LLC-R020",
        category="Evidence completeness",
        severity=Severity.WARNING,
        title="Evidence completeness gate",
        description="One finding was excluded from the formal result.",
        evidence=(
            {
                "source": "rule_definition",
                "description": "R020 requires evidence for WARNING findings.",
                "references": ["LLC-R999"],
            },
        ),
        requires_engineer_confirmation=True,
    )
    result = ReviewResult(
        summary=ReviewSummary.model_validate(
            {
                "pass": 0,
                "info": 0,
                "warning": 1,
                "critical": 0,
                "insufficient_data": 0,
            }
        ),
        findings=(gate,),
        excluded_findings=(excluded,),
    )
    monkeypatch.setattr(review_service, "run_design_review", lambda _context: result)
    project = (await api_client.post("/projects", json=api_project_payload)).json()

    run_response = await api_client.post(f"/projects/{project['id']}/review")
    latest_response = await api_client.get(f"/projects/{project['id']}/review")
    report_response = await api_client.get(f"/projects/{project['id']}/report")

    assert run_response.status_code == 201
    response = run_response.json()
    assert [finding["rule_id"] for finding in response["findings"]] == ["LLC-R020"]
    assert [
        finding["rule_id"] for finding in response["excluded_findings"]
    ] == ["LLC-R999"]
    assert response["excluded_findings"][0]["report_eligible"] is False
    assert latest_response.json() == response

    with api_session_factory() as session:
        stored = session.scalars(
            select(ReviewFinding).order_by(ReviewFinding.position)
        ).all()
    assert [(finding.rule_id, finding.report_eligible) for finding in stored] == [
        ("LLC-R020", True),
        ("LLC-R999", False),
    ]
    assert report_response.status_code == 200
    assert "LLC-R020" in report_response.text
    assert "Unsupported warning must remain auditable" not in report_response.text
