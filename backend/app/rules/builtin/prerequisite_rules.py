from collections.abc import Sequence

from app.engine.exceptions import EngineeringCalculationError
from app.engine.units import normalize_positive_quantity, normalize_transformer_ratio
from app.rules.base import ReviewRule
from app.rules.helpers import (
    insufficient_finding,
    rule_definition_evidence,
    user_input_evidence,
)
from app.schemas.review import EvidenceItem, EvidenceSource, Finding, ReviewContext, Severity


class DeadTimeInformationRule(ReviewRule):
    rule_id = "LLC-R017"
    category = "control"
    title = "Dead-time information"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        rule_evidence = rule_definition_evidence(
            self.rule_id,
            "R017 requires dead-time information only when ZVS analysis is requested.",
        )
        if not context.requests.zvs_analysis_requested:
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=Severity.INFO,
                title=self.title,
                description="ZVS analysis is not requested, so dead-time is not required by this review.",
                evidence=(rule_evidence,),
                requires_engineer_confirmation=False,
            )

        dead_time = context.project.dead_time
        input_evidence = user_input_evidence(
            "Dead-time supplied for requested ZVS analysis.", dead_time=dead_time
        )
        if dead_time is None:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="ZVS analysis is requested but dead-time information is missing.",
                missing_information=("project.dead_time",),
                recommended_action=("Provide dead-time with an explicit time unit.",),
                evidence=(rule_evidence,),
            )
        try:
            normalize_positive_quantity(
                name="dead_time", quantity=dead_time, target_unit="s"
            )
        except EngineeringCalculationError:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Dead-time information is not a valid positive time quantity.",
                missing_information=("valid_project.dead_time",),
                recommended_action=("Correct the dead-time value or unit.",),
                evidence=(input_evidence, rule_evidence),
            )

        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=Severity.PASS,
            title=self.title,
            description="Dead-time information is present for the requested ZVS analysis prerequisite.",
            evidence=(input_evidence, rule_evidence),
            requires_engineer_confirmation=False,
        )


class TransformerRatioRequiredRule(ReviewRule):
    rule_id = "LLC-R018"
    category = "transformer"
    title = "Transformer ratio required"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        rule_evidence = rule_definition_evidence(
            self.rule_id,
            "R018 requires transformer ratio before a full gain review.",
        )
        if not context.requests.full_gain_review_requested:
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=Severity.INFO,
                title=self.title,
                description="Full gain review is not requested, so transformer ratio is not required by this rule.",
                evidence=(rule_evidence,),
                requires_engineer_confirmation=False,
            )

        ratio = context.project.transformer_ratio
        input_evidence = user_input_evidence(
            "Transformer ratio supplied for gain review.", transformer_ratio=ratio
        )
        if ratio is None:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Full gain review is requested but transformer ratio is missing.",
                missing_information=("project.transformer_ratio",),
                recommended_action=("Provide the transformer ratio as a positive dimensionless quantity.",),
                evidence=(rule_evidence,),
            )
        try:
            normalize_transformer_ratio(ratio)
        except EngineeringCalculationError:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Transformer ratio is not a valid positive dimensionless quantity.",
                missing_information=("valid_project.transformer_ratio",),
                recommended_action=("Correct the transformer ratio value or unit.",),
                evidence=(input_evidence, rule_evidence),
            )

        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=Severity.PASS,
            title=self.title,
            description="Transformer ratio is available as a prerequisite; no gain calculation is performed by this rule.",
            evidence=(input_evidence, rule_evidence),
            requires_engineer_confirmation=False,
        )


class GainReviewPrerequisiteRule(ReviewRule):
    rule_id = "LLC-R019"
    category = "resonant_tank"
    title = "Gain review prerequisites"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        rule_evidence = rule_definition_evidence(
            self.rule_id,
            "R019 checks only configured prerequisite presence and does not calculate LLC gain.",
        )
        if not context.requests.full_gain_review_requested:
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=Severity.INFO,
                title=self.title,
                description="Full gain review is not requested, so gain prerequisites are not evaluated.",
                evidence=(rule_evidence,),
                requires_engineer_confirmation=False,
            )

        required = context.settings.gain_review_required_parameters
        if not required:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Full gain review is requested but its required parameter list is not configured.",
                missing_information=("settings.gain_review_required_parameters",),
                recommended_action=(
                    "Configure the project-approved gain prerequisite list; do not let the model invent missing parameters.",
                ),
                evidence=(rule_evidence,),
            )

        missing = tuple(
            parameter.value
            for parameter in required
            if getattr(context.project, parameter.value) is None
        )
        configured_evidence = EvidenceItem(
            source=EvidenceSource.RULE_DEFINITION,
            description="Project-configured gain review prerequisite list.",
            references=tuple(parameter.value for parameter in required),
        )
        if missing:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Configured gain review prerequisites are incomplete.",
                missing_information=missing,
                recommended_action=("Provide every configured gain prerequisite before gain review.",),
                evidence=(rule_evidence, configured_evidence),
            )

        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=Severity.PASS,
            title=self.title,
            description="All project-configured gain review prerequisites are present; gain itself was not calculated.",
            evidence=(rule_evidence, configured_evidence),
            requires_engineer_confirmation=False,
        )


class EvidenceCompletenessRule(ReviewRule):
    rule_id = "LLC-R020"
    category = "evidence_integrity"
    title = "Evidence completeness"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        invalid_findings = tuple(
            finding.rule_id
            for finding in prior_findings
            if finding.severity in {Severity.WARNING, Severity.CRITICAL}
            and not finding.evidence
        )
        rule_evidence = EvidenceItem(
            source=EvidenceSource.RULE_DEFINITION,
            description="R020 requires at least one evidence item for every WARNING or CRITICAL finding.",
            references=(self.rule_id, *invalid_findings),
        )
        if invalid_findings:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="One or more WARNING/CRITICAL findings lack evidence and are not eligible for formal reporting.",
                missing_information=tuple(
                    f"evidence:{rule_id}" for rule_id in invalid_findings
                ),
                recommended_action=("Attach traceable evidence or remove the unsupported finding.",),
                evidence=(rule_evidence,),
            )

        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=Severity.PASS,
            title=self.title,
            description="Every WARNING and CRITICAL finding contains traceable evidence.",
            evidence=(rule_evidence,),
            requires_engineer_confirmation=False,
        )
