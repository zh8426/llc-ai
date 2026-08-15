from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.project import Project
from app.models.review import (
    ReviewCalculationSnapshot,
    ReviewFinding,
    ReviewProjectSnapshot,
    ReviewRun,
)
from app.rules import run_design_review
from app.schemas.engineering import CalculationSnapshot
from app.schemas.project import ProjectReviewResponse
from app.schemas.review import (
    ControllerReviewInput,
    Finding,
    LLCProjectReviewInput,
    MOSFETReviewInput,
    ResonantCapacitorReviewInput,
    ReviewContext,
    ReviewParameterName,
    ReviewRequests,
    ReviewSettings,
    ReviewSummary,
)
from app.services.calculations import calculate_project
from app.services.projects import (
    CONTROLLER_QUANTITIES,
    PRIMARY_SWITCH_QUANTITIES,
    RESONANT_CAPACITOR_QUANTITIES,
    nested_quantity,
    project_quantity,
    project_to_response,
)


def build_review_context(
    project: Project,
    calculation_snapshot: CalculationSnapshot,
) -> ReviewContext:
    settings_parameters = project.gain_review_required_parameters
    return ReviewContext(
        project=LLCProjectReviewInput(
            vin_min=project_quantity(project, "vin_min"),
            vin_nom=project_quantity(project, "vin_nom"),
            vin_max=project_quantity(project, "vin_max"),
            vout=project_quantity(project, "vout"),
            pout=project_quantity(project, "pout"),
            iout=project_quantity(project, "iout"),
            lr=project_quantity(project, "lr"),
            lm=project_quantity(project, "lm"),
            cr=project_quantity(project, "cr"),
            fsw_min=project_quantity(project, "fsw_min"),
            fsw_max=project_quantity(project, "fsw_max"),
            transformer_ratio=project_quantity(project, "transformer_ratio"),
            dead_time=project_quantity(project, "dead_time"),
        ),
        mosfet=MOSFETReviewInput(
            vds_rating=nested_quantity(
                project, "vds_rating", PRIMARY_SWITCH_QUANTITIES
            ),
            measured_vds_peak=nested_quantity(
                project, "measured_vds_peak", PRIMARY_SWITCH_QUANTITIES
            ),
            current_rating=nested_quantity(
                project, "current_rating", PRIMARY_SWITCH_QUANTITIES
            ),
            measured_peak_current=nested_quantity(
                project, "measured_peak_current", PRIMARY_SWITCH_QUANTITIES
            ),
            current_temperature_condition=(
                project.primary_switch_current_temperature_condition
            ),
        ),
        resonant_capacitor=ResonantCapacitorReviewInput(
            voltage_rating=nested_quantity(
                project, "voltage_rating", RESONANT_CAPACITOR_QUANTITIES
            ),
            voltage_stress=nested_quantity(
                project, "voltage_stress", RESONANT_CAPACITOR_QUANTITIES
            ),
            rms_current_rating=nested_quantity(
                project, "rms_current_rating", RESONANT_CAPACITOR_QUANTITIES
            ),
            rms_current_stress=nested_quantity(
                project, "rms_current_stress", RESONANT_CAPACITOR_QUANTITIES
            ),
        ),
        controller=ControllerReviewInput(
            frequency_min=nested_quantity(
                project, "frequency_min", CONTROLLER_QUANTITIES
            ),
            frequency_max=nested_quantity(
                project, "frequency_max", CONTROLLER_QUANTITIES
            ),
        ),
        requests=ReviewRequests(
            zvs_analysis_requested=project.zvs_analysis_requested,
            full_gain_review_requested=project.full_gain_review_requested,
        ),
        settings=ReviewSettings(
            output_power_relative_tolerance=(
                project.output_power_relative_tolerance
            ),
            measured_vds_required_margin_ratio=(
                project.measured_vds_required_margin_ratio
            ),
            gain_review_required_parameters=(
                tuple(ReviewParameterName(value) for value in settings_parameters)
                if settings_parameters is not None
                else None
            ),
        ),
        calculated_inputs={
            result.name: result for result in calculation_snapshot.calculations
        },
    )


def run_and_store_review(session: Session, project: Project) -> ReviewRun:
    calculation_snapshot = calculate_project(project)
    result = run_design_review(build_review_context(project, calculation_snapshot))
    review = ReviewRun(
        project_id=project.id,
        pass_count=result.summary.pass_count,
        info_count=result.summary.info,
        warning_count=result.summary.warning,
        critical_count=result.summary.critical,
        insufficient_data_count=result.summary.insufficient_data,
    )
    review.project_snapshot = ReviewProjectSnapshot(
        project_data=project_to_response(project).model_dump(mode="json")
    )
    serialized_calculations = [
        calculation.model_dump(mode="json")
        for calculation in calculation_snapshot.calculations
    ]
    review.calculation_snapshot = ReviewCalculationSnapshot(
        calculated_at=calculation_snapshot.calculated_at,
        engine_version=calculation_snapshot.engine_version,
        calculations=serialized_calculations,
        missing_information=list(calculation_snapshot.missing_information),
        errors=calculation_snapshot.errors,
    )
    all_findings = (*result.findings, *result.excluded_findings)
    for position, finding in enumerate(all_findings):
        serialized = finding.model_dump(mode="json")
        review.findings.append(
            ReviewFinding(
                position=position,
                rule_id=finding.rule_id,
                category=finding.category,
                severity=finding.severity.value,
                title=finding.title,
                description=finding.description,
                evidence=serialized["evidence"],
                calculated_values=serialized["calculated_values"],
                missing_information=serialized["missing_information"],
                recommended_action=serialized["recommended_action"],
                requires_engineer_confirmation=(
                    finding.requires_engineer_confirmation
                ),
                report_eligible=finding.report_eligible,
            )
        )
    session.add(review)
    session.commit()
    return get_review(session, review.id)


def get_review(session: Session, review_id: str) -> ReviewRun:
    statement = (
        select(ReviewRun)
        .where(ReviewRun.id == review_id)
        .options(
            selectinload(ReviewRun.findings),
            selectinload(ReviewRun.project_snapshot),
            selectinload(ReviewRun.calculation_snapshot),
        )
    )
    review = session.scalar(statement)
    if review is None:
        raise LookupError(review_id)
    return review


def get_latest_review(session: Session, project_id: str) -> ReviewRun | None:
    statement = (
        select(ReviewRun)
        .where(ReviewRun.project_id == project_id)
        .order_by(ReviewRun.created_at.desc(), ReviewRun.id.desc())
        .limit(1)
        .options(
            selectinload(ReviewRun.findings),
            selectinload(ReviewRun.project_snapshot),
            selectinload(ReviewRun.calculation_snapshot),
        )
    )
    return session.scalar(statement)


def review_to_response(review: ReviewRun) -> ProjectReviewResponse:
    stored_findings = tuple(
        Finding.model_validate(
            {
                "rule_id": finding.rule_id,
                "category": finding.category,
                "severity": finding.severity,
                "title": finding.title,
                "description": finding.description,
                "evidence": finding.evidence,
                "calculated_values": finding.calculated_values,
                "missing_information": finding.missing_information,
                "recommended_action": finding.recommended_action,
                "requires_engineer_confirmation": (
                    finding.requires_engineer_confirmation
                ),
                "report_eligible": finding.report_eligible,
            }
        )
        for finding in review.findings
    )
    findings = tuple(
        finding for finding in stored_findings if finding.report_eligible
    )
    excluded_findings = tuple(
        finding for finding in stored_findings if not finding.report_eligible
    )
    return ProjectReviewResponse(
        project_id=review.project_id,
        review_id=review.id,
        created_at=(
            review.created_at.replace(tzinfo=UTC)
            if review.created_at.tzinfo is None
            else review.created_at.astimezone(UTC)
        ),
        summary=ReviewSummary.model_validate(
            {
                "pass": review.pass_count,
                "info": review.info_count,
                "warning": review.warning_count,
                "critical": review.critical_count,
                "insufficient_data": review.insufficient_data_count,
            }
        ),
        findings=findings,
        excluded_findings=excluded_findings,
        calculation_snapshot=(
            CalculationSnapshot.model_validate(
                {
                    "project_id": review.project_id,
                    "calculated_at": (
                        review.calculation_snapshot.calculated_at.replace(tzinfo=UTC)
                        if review.calculation_snapshot.calculated_at.tzinfo is None
                        else review.calculation_snapshot.calculated_at.astimezone(UTC)
                    ),
                    "engine_version": review.calculation_snapshot.engine_version,
                    "calculations": review.calculation_snapshot.calculations,
                    "missing_information": (
                        review.calculation_snapshot.missing_information
                    ),
                    "errors": review.calculation_snapshot.errors,
                }
            )
            if review.calculation_snapshot is not None
            else None
        ),
    )
