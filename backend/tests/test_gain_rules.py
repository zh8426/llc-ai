from app.rules.builtin import (
    FHAApplicabilityRule,
    FrequencyCapabilityRule,
    GainModelPrerequisitesRule,
    GainPeakMarginRule,
    OperatingPointRegionRule,
    RequiredGainCoverageRule,
)
from app.schemas.engineering import EngineeringQuantity
from app.schemas.review import ReviewContext, ReviewRequests, Severity


def quantity(value: float, unit: str) -> EngineeringQuantity:
    return EngineeringQuantity(value=value, unit=unit)


def update_project(context: ReviewContext, **changes: object) -> ReviewContext:
    return context.model_copy(
        update={"project": context.project.model_copy(update=changes)}
    )


def test_gain_rules_report_normal_envelope(
    normal_review_context: ReviewContext,
) -> None:
    findings = (
        GainModelPrerequisitesRule().evaluate(normal_review_context),
        RequiredGainCoverageRule().evaluate(normal_review_context),
        OperatingPointRegionRule().evaluate(normal_review_context),
        FrequencyCapabilityRule().evaluate(normal_review_context),
        GainPeakMarginRule().evaluate(normal_review_context),
        FHAApplicabilityRule().evaluate(normal_review_context),
    )

    assert [finding.severity for finding in findings] == [
        Severity.PASS,
        Severity.PASS,
        Severity.PASS,
        Severity.PASS,
        Severity.INFO,
        Severity.INFO,
    ]
    assert all(finding.evidence for finding in findings)


def test_gain_prerequisite_rule_is_insufficient_when_requested_inputs_are_missing(
    incomplete_review_context: ReviewContext,
) -> None:
    finding = GainModelPrerequisitesRule().evaluate(incomplete_review_context)

    assert finding.severity == Severity.INSUFFICIENT_DATA
    assert "vin_min" in finding.missing_information
    assert "transformer_ratio" in finding.missing_information


def test_gain_rules_are_informational_when_full_review_is_not_requested() -> None:
    context = ReviewContext(
        requests=ReviewRequests(full_gain_review_requested=False)
    )

    assert GainModelPrerequisitesRule().evaluate(context).severity == Severity.INFO
    assert RequiredGainCoverageRule().evaluate(context).severity == Severity.INFO


def test_operating_region_rule_warns_for_capacitive_nominal_root(
    normal_review_context: ReviewContext,
) -> None:
    context = update_project(
        normal_review_context,
        vin_min=quantity(300, "V"),
        vin_nom=quantity(360, "V"),
        vin_max=quantity(420, "V"),
        transformer_ratio=quantity(4.17, "dimensionless"),
        fsw_min=quantity(40, "kHz"),
        fsw_max=quantity(70, "kHz"),
    )

    finding = OperatingPointRegionRule().evaluate(context)

    assert finding.severity == Severity.WARNING
    assert "ZVS" in finding.description
