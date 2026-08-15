from collections import Counter
from collections.abc import Sequence

from app.rules.base import ReviewRule
from app.rules.definitions import BUILTIN_RULES
from app.schemas.review import (
    ReviewContext,
    ReviewResult,
    ReviewSummary,
    Severity,
)


class ReviewEngine:
    """Run deterministic rules and enforce the R020 evidence gate."""

    def __init__(self, rules: Sequence[ReviewRule] = BUILTIN_RULES) -> None:
        self._rules = tuple(rules)
        rule_ids = [rule.rule_id for rule in self._rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("Review rule IDs must be unique")
        if rule_ids.count("LLC-R020") != 1:
            raise ValueError("Review engine requires exactly one LLC-R020 evidence rule")

    @property
    def rules(self) -> tuple[ReviewRule, ...]:
        return self._rules

    def run(self, context: ReviewContext) -> ReviewResult:
        evidence_rule = next(rule for rule in self._rules if rule.rule_id == "LLC-R020")
        evaluated = tuple(
            rule.evaluate(context)
            for rule in self._rules
            if rule.rule_id != "LLC-R020"
        )

        excluded = tuple(
            finding.model_copy(update={"report_eligible": False})
            for finding in evaluated
            if finding.severity in {Severity.WARNING, Severity.CRITICAL}
            and not finding.evidence
        )
        excluded_ids = {finding.rule_id for finding in excluded}
        eligible = tuple(
            finding for finding in evaluated if finding.rule_id not in excluded_ids
        )
        evidence_finding = evidence_rule.evaluate(context, prior_findings=evaluated)
        findings = (*eligible, evidence_finding)

        counts = Counter(finding.severity for finding in findings)
        summary = ReviewSummary.model_validate(
            {
                "pass": counts[Severity.PASS],
                "info": counts[Severity.INFO],
                "warning": counts[Severity.WARNING],
                "critical": counts[Severity.CRITICAL],
                "insufficient_data": counts[Severity.INSUFFICIENT_DATA],
            }
        )
        return ReviewResult(
            summary=summary,
            findings=findings,
            excluded_findings=excluded,
        )


def run_design_review(context: ReviewContext) -> ReviewResult:
    return ReviewEngine().run(context)
