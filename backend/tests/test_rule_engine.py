from collections.abc import Sequence

import pytest

from app.rules.base import ReviewRule
from app.rules.builtin import (
    CriticalParameterCompletenessRule,
    EvidenceCompletenessRule,
)
from app.rules.definitions import BUILTIN_RULES
from app.rules.engine import ReviewEngine, run_design_review
from app.schemas.review import Finding, ReviewContext, Severity


class UnsupportedWarningRule(ReviewRule):
    rule_id = "LLC-R999"
    category = "test"
    title = "Unsupported warning"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=Severity.WARNING,
            title=self.title,
            description="This synthetic warning intentionally has no evidence.",
            recommended_action=("Add evidence.",),
            requires_engineer_confirmation=False,
        )


def test_builtin_registry_contains_r001_through_r026_in_order() -> None:
    assert [rule.rule_id for rule in BUILTIN_RULES] == [
        f"LLC-R{number:03d}" for number in range(1, 27)
    ]


def test_review_engine_exposes_immutable_rule_order() -> None:
    engine = ReviewEngine()

    assert engine.rules == BUILTIN_RULES
    assert isinstance(engine.rules, tuple)


def test_normal_context_returns_twenty_six_eligible_findings(
    normal_review_context: ReviewContext,
) -> None:
    result = run_design_review(normal_review_context)

    assert len(result.findings) == 26
    assert result.excluded_findings == ()
    assert result.summary.model_dump(by_alias=True) == {
        "pass": 16,
        "info": 9,
        "warning": 1,
        "critical": 0,
        "insufficient_data": 0,
    }


def test_incomplete_context_returns_structured_missing_information(
    incomplete_review_context: ReviewContext,
) -> None:
    result = run_design_review(incomplete_review_context)

    assert len(result.findings) == 26
    assert result.summary.insufficient_data >= 10
    assert any(finding.missing_information for finding in result.findings)


def test_invalid_context_produces_critical_findings_with_evidence(
    invalid_review_context: ReviewContext,
) -> None:
    result = run_design_review(invalid_review_context)
    critical = [
        finding for finding in result.findings if finding.severity == Severity.CRITICAL
    ]

    assert {finding.rule_id for finding in critical} >= {"LLC-R002", "LLC-R003", "LLC-R004"}
    assert all(finding.evidence for finding in critical)


def test_every_builtin_warning_and_critical_contains_evidence(
    normal_review_context: ReviewContext,
    invalid_review_context: ReviewContext,
) -> None:
    for context in (normal_review_context, invalid_review_context):
        result = run_design_review(context)
        assert all(
            finding.evidence
            for finding in result.findings
            if finding.severity in {Severity.WARNING, Severity.CRITICAL}
        )


def test_r020_excludes_unsupported_warning_from_formal_findings() -> None:
    engine = ReviewEngine((UnsupportedWarningRule(), EvidenceCompletenessRule()))

    result = engine.run(ReviewContext())

    assert [finding.rule_id for finding in result.findings] == ["LLC-R020"]
    assert result.findings[0].severity == Severity.INSUFFICIENT_DATA
    assert len(result.excluded_findings) == 1
    assert result.excluded_findings[0].rule_id == "LLC-R999"
    assert result.excluded_findings[0].report_eligible is False


def test_review_engine_requires_unique_rule_ids() -> None:
    with pytest.raises(ValueError, match="unique"):
        ReviewEngine((EvidenceCompletenessRule(), EvidenceCompletenessRule()))


def test_review_engine_requires_evidence_gate() -> None:
    with pytest.raises(ValueError, match="R020"):
        ReviewEngine((CriticalParameterCompletenessRule(),))


def test_review_execution_is_deterministic(normal_review_context: ReviewContext) -> None:
    first = run_design_review(normal_review_context).model_dump(mode="json")
    second = run_design_review(normal_review_context).model_dump(mode="json")

    assert first == second
