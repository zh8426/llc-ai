from collections.abc import Sequence

from app.engine.exceptions import EngineeringCalculationError
from app.engine.units import normalize_positive_quantity
from app.rules.base import ReviewRule
from app.rules.helpers import (
    insufficient_finding,
    rule_definition_evidence,
    user_input_evidence,
)
from app.schemas.engineering import EngineeringQuantity
from app.schemas.review import Finding, ReviewContext, Severity


class CriticalParameterCompletenessRule(ReviewRule):
    rule_id = "LLC-R001"
    category = "input_integrity"
    title = "Critical parameter completeness"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        project = context.project
        required = {
            "vin_min": project.vin_min,
            "vin_nom": project.vin_nom,
            "vin_max": project.vin_max,
            "vout": project.vout,
            "pout": project.pout,
            "lr": project.lr,
            "lm": project.lm,
            "cr": project.cr,
            "fsw_min": project.fsw_min,
            "fsw_max": project.fsw_max,
        }
        missing = tuple(name for name, value in required.items() if value is None)
        evidence = (
            user_input_evidence(
                "Critical project parameters supplied by the user.", **required
            ),
            rule_definition_evidence(
                self.rule_id,
                "R001 requires the project voltage, power, resonant tank, and switching range inputs.",
            ),
        )
        if missing:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="The design review cannot establish a complete core input set.",
                missing_information=missing,
                recommended_action=("Provide every missing core project parameter with an explicit unit.",),
                evidence=evidence,
            )

        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=Severity.PASS,
            title=self.title,
            description="All critical Phase 2 project parameters are present.",
            evidence=evidence,
            requires_engineer_confirmation=False,
        )


class PositiveValuesRule(ReviewRule):
    rule_id = "LLC-R002"
    category = "input_integrity"
    title = "Positive engineering values"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        project = context.project
        specifications: tuple[tuple[str, EngineeringQuantity | None, str], ...] = (
            ("vin_min", project.vin_min, "V"),
            ("vin_nom", project.vin_nom, "V"),
            ("vin_max", project.vin_max, "V"),
            ("vout", project.vout, "V"),
            ("pout", project.pout, "W"),
            ("lr", project.lr, "H"),
            ("lm", project.lm, "H"),
            ("cr", project.cr, "F"),
            ("fsw_min", project.fsw_min, "Hz"),
            ("fsw_max", project.fsw_max, "Hz"),
        )
        missing = tuple(name for name, value, _ in specifications if value is None)
        invalid: list[str] = []
        for name, value, target_unit in specifications:
            if value is None:
                continue
            try:
                normalize_positive_quantity(
                    name=name,
                    quantity=value,
                    target_unit=target_unit,
                )
            except EngineeringCalculationError:
                invalid.append(name)

        values = {name: value for name, value, _ in specifications}
        evidence = (
            user_input_evidence("Project values checked by R002.", **values),
            rule_definition_evidence(
                self.rule_id,
                "R002 requires positive voltage, power, inductance, capacitance, and frequency values.",
            ),
        )
        if invalid:
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=Severity.CRITICAL,
                title=self.title,
                description="One or more supplied core values are non-positive or use an incompatible unit.",
                evidence=evidence,
                missing_information=tuple(invalid),
                recommended_action=("Correct the listed values and units before running engineering calculations.",),
                requires_engineer_confirmation=False,
            )
        if missing:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Positive-value validation is incomplete because core values are missing.",
                missing_information=missing,
                recommended_action=("Provide the missing values with explicit units.",),
                evidence=evidence,
            )

        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=Severity.PASS,
            title=self.title,
            description="All supplied core voltage, power, resonant tank, and frequency values are positive and dimensionally valid.",
            evidence=evidence,
            requires_engineer_confirmation=False,
        )


class InputVoltageOrderingRule(ReviewRule):
    rule_id = "LLC-R003"
    category = "input_integrity"
    title = "Input voltage ordering"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        project = context.project
        supplied = {
            "vin_min": project.vin_min,
            "vin_nom": project.vin_nom,
            "vin_max": project.vin_max,
        }
        missing = tuple(name for name, value in supplied.items() if value is None)
        evidence = (
            user_input_evidence("Input voltage range supplied by the user.", **supplied),
            rule_definition_evidence(
                self.rule_id, "R003 requires Vin Min <= Vin Nom <= Vin Max."
            ),
        )
        if missing:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="The input voltage ordering cannot be evaluated.",
                missing_information=missing,
                recommended_action=("Provide Vin Min, Vin Nom, and Vin Max.",),
                evidence=evidence,
            )

        try:
            vin_min = normalize_positive_quantity(
                name="vin_min", quantity=project.vin_min, target_unit="V"
            )
            vin_nom = normalize_positive_quantity(
                name="vin_nom", quantity=project.vin_nom, target_unit="V"
            )
            vin_max = normalize_positive_quantity(
                name="vin_max", quantity=project.vin_max, target_unit="V"
            )
        except EngineeringCalculationError:
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=Severity.CRITICAL,
                title=self.title,
                description="The input voltage range contains invalid values or units.",
                evidence=evidence,
                missing_information=("valid_vin_range",),
                recommended_action=("Correct the input voltage values and units.",),
                requires_engineer_confirmation=False,
            )

        if vin_min.value <= vin_nom.value <= vin_max.value:
            severity = Severity.PASS
            description = "Vin Min <= Vin Nom <= Vin Max."
            action: tuple[str, ...] = ()
        else:
            severity = Severity.CRITICAL
            description = "The supplied input voltage range is not ordered as Vin Min <= Vin Nom <= Vin Max."
            action = ("Correct the project input voltage definitions before review.",)

        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=severity,
            title=self.title,
            description=description,
            evidence=evidence,
            recommended_action=action,
            requires_engineer_confirmation=False,
        )


class SwitchingFrequencyOrderingRule(ReviewRule):
    rule_id = "LLC-R004"
    category = "input_integrity"
    title = "Switching frequency ordering"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        project = context.project
        supplied = {"fsw_min": project.fsw_min, "fsw_max": project.fsw_max}
        missing = tuple(name for name, value in supplied.items() if value is None)
        evidence = (
            user_input_evidence("Switching frequency range supplied by the user.", **supplied),
            rule_definition_evidence(
                self.rule_id, "R004 requires Fsw Min < Fsw Max."
            ),
        )
        if missing:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="The switching frequency ordering cannot be evaluated.",
                missing_information=missing,
                recommended_action=("Provide Fsw Min and Fsw Max.",),
                evidence=evidence,
            )

        try:
            fsw_min = normalize_positive_quantity(
                name="fsw_min", quantity=project.fsw_min, target_unit="Hz"
            )
            fsw_max = normalize_positive_quantity(
                name="fsw_max", quantity=project.fsw_max, target_unit="Hz"
            )
        except EngineeringCalculationError:
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=Severity.CRITICAL,
                title=self.title,
                description="The switching frequency range contains invalid values or units.",
                evidence=evidence,
                missing_information=("valid_switching_frequency_range",),
                recommended_action=("Correct the switching frequency values and units.",),
                requires_engineer_confirmation=False,
            )

        if fsw_min.value < fsw_max.value:
            severity = Severity.PASS
            description = "Fsw Min is lower than Fsw Max."
            action: tuple[str, ...] = ()
        else:
            severity = Severity.CRITICAL
            description = "Fsw Min must be strictly lower than Fsw Max."
            action = ("Correct the project switching frequency range before review.",)

        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=severity,
            title=self.title,
            description=description,
            evidence=evidence,
            recommended_action=action,
            requires_engineer_confirmation=False,
        )

