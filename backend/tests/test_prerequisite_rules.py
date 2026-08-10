from collections.abc import Callable

from app.rules.builtin import (
    DeadTimeInformationRule,
    EvidenceCompletenessRule,
    GainReviewPrerequisiteRule,
    TransformerRatioRequiredRule,
)
from app.schemas.engineering import EngineeringQuantity
from app.schemas.review import Finding, ReviewContext, ReviewParameterName, Severity


def q(value: float, unit: str) -> EngineeringQuantity:
    return EngineeringQuantity(value=value, unit=unit)


def test_r017_is_info_when_zvs_analysis_is_not_requested(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    context = update_review_context(
        normal_review_context, "requests", zvs_analysis_requested=False
    )

    assert DeadTimeInformationRule().evaluate(context).severity == Severity.INFO


def test_r017_passes_valid_dead_time_prerequisite(
    normal_review_context: ReviewContext,
) -> None:
    assert DeadTimeInformationRule().evaluate(normal_review_context).severity == Severity.PASS


def test_r017_handles_missing_and_invalid_dead_time(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    missing = update_review_context(normal_review_context, "project", dead_time=None)
    invalid = update_review_context(normal_review_context, "project", dead_time=q(300, "V"))

    assert DeadTimeInformationRule().evaluate(missing).severity == Severity.INSUFFICIENT_DATA
    assert DeadTimeInformationRule().evaluate(invalid).severity == Severity.INSUFFICIENT_DATA


def test_r018_is_info_when_gain_review_is_not_requested(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    context = update_review_context(
        normal_review_context, "requests", full_gain_review_requested=False
    )

    assert TransformerRatioRequiredRule().evaluate(context).severity == Severity.INFO


def test_r018_passes_valid_transformer_ratio_prerequisite(
    normal_review_context: ReviewContext,
) -> None:
    assert TransformerRatioRequiredRule().evaluate(normal_review_context).severity == Severity.PASS


def test_r018_handles_missing_and_invalid_transformer_ratio(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    missing = update_review_context(
        normal_review_context, "project", transformer_ratio=None
    )
    invalid = update_review_context(
        normal_review_context, "project", transformer_ratio=q(4, "V")
    )

    assert TransformerRatioRequiredRule().evaluate(missing).severity == Severity.INSUFFICIENT_DATA
    assert TransformerRatioRequiredRule().evaluate(invalid).severity == Severity.INSUFFICIENT_DATA


def test_r019_is_info_when_gain_review_is_not_requested(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    context = update_review_context(
        normal_review_context, "requests", full_gain_review_requested=False
    )

    assert GainReviewPrerequisiteRule().evaluate(context).severity == Severity.INFO


def test_r019_passes_project_configured_prerequisite_presence(
    normal_review_context: ReviewContext,
) -> None:
    finding = GainReviewPrerequisiteRule().evaluate(normal_review_context)

    assert finding.severity == Severity.PASS
    assert "gain itself was not calculated" in finding.description


def test_r019_requires_explicit_prerequisite_configuration(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    context = update_review_context(
        normal_review_context, "settings", gain_review_required_parameters=None
    )

    finding = GainReviewPrerequisiteRule().evaluate(context)

    assert finding.severity == Severity.INSUFFICIENT_DATA
    assert "settings.gain_review_required_parameters" in finding.missing_information


def test_r019_reports_missing_configured_parameter(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    settings_context = update_review_context(
        normal_review_context,
        "settings",
        gain_review_required_parameters=(
            ReviewParameterName.LR,
            ReviewParameterName.TRANSFORMER_RATIO,
        ),
    )
    context = update_review_context(
        settings_context, "project", transformer_ratio=None
    )

    finding = GainReviewPrerequisiteRule().evaluate(context)

    assert finding.severity == Severity.INSUFFICIENT_DATA
    assert finding.missing_information == ("transformer_ratio",)


def test_r020_passes_supported_findings() -> None:
    supported = Finding(
        rule_id="LLC-R010",
        category="test",
        severity=Severity.PASS,
        title="Supported",
        description="No evidence is required for this synthetic PASS finding.",
        requires_engineer_confirmation=False,
    )

    finding = EvidenceCompletenessRule().evaluate(
        ReviewContext(), prior_findings=(supported,)
    )

    assert finding.severity == Severity.PASS


def test_r020_flags_warning_without_evidence() -> None:
    unsupported = Finding(
        rule_id="LLC-R010",
        category="test",
        severity=Severity.WARNING,
        title="Unsupported",
        description="Synthetic unsupported warning.",
        requires_engineer_confirmation=False,
    )

    finding = EvidenceCompletenessRule().evaluate(
        ReviewContext(), prior_findings=(unsupported,)
    )

    assert finding.severity == Severity.INSUFFICIENT_DATA
    assert finding.missing_information == ("evidence:LLC-R010",)
    assert finding.evidence

