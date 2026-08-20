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


def test_gain_rules_report_covered_inductive_envelope(
    normal_review_context: ReviewContext,
) -> None:
    context = update_project(
        normal_review_context,
        lm=quantity(150, "uH"),
        fsw_min=quantity(50, "kHz"),
        fsw_max=quantity(180, "kHz"),
    )
    findings = (
        GainModelPrerequisitesRule().evaluate(context),
        RequiredGainCoverageRule().evaluate(context),
        OperatingPointRegionRule().evaluate(context),
        FrequencyCapabilityRule().evaluate(context),
        GainPeakMarginRule().evaluate(context),
        FHAApplicabilityRule().evaluate(context),
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


def test_required_gain_coverage_warns_when_low_line_gain_is_not_covered(
    normal_review_context: ReviewContext,
) -> None:
    finding = RequiredGainCoverageRule().evaluate(normal_review_context)

    assert finding.severity == Severity.WARNING
    assert (
        finding.calculated_values["available_gain_max"].value
        < finding.calculated_values["required_gain_at_vin_min"].value
    )


def test_gain_rules_do_not_use_capacitive_peak_as_available_gain(
    normal_review_context: ReviewContext,
) -> None:
    context = update_project(
        normal_review_context,
        fsw_min=quantity(40, "kHz"),
        fsw_max=quantity(60, "kHz"),
    )

    coverage = RequiredGainCoverageRule().evaluate(context)
    peak = GainPeakMarginRule().evaluate(context)

    assert coverage.severity == Severity.WARNING
    assert "inductive" in coverage.description
    assert "available_gain_max" not in coverage.calculated_values
    assert peak.severity == Severity.INSUFFICIENT_DATA
    assert peak.missing_information == ("inductive_fha_gain_point",)


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
