from collections.abc import Sequence

from app.engine import calculate_fp, calculate_fr, calculate_lm_lr_ratio, calculate_zr
from app.engine.exceptions import EngineeringCalculationError
from app.engine.units import normalize_positive_quantity
from app.rules.base import ReviewRule
from app.rules.helpers import (
    calculation_evidence,
    insufficient_finding,
    rule_definition_evidence,
    user_input_evidence,
)
from app.schemas.engineering import CalculationResult, EngineeringQuantity
from app.schemas.review import Finding, ReviewContext, Severity


class ResonantFrequencyCalculationRule(ReviewRule):
    rule_id = "LLC-R005"
    category = "resonant_tank"
    title = "Resonant frequency calculation"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        project = context.project
        missing = tuple(
            name for name, value in {"lr": project.lr, "cr": project.cr}.items() if value is None
        )
        input_evidence = user_input_evidence(
            "Resonant tank inputs supplied for fr calculation.",
            lr=project.lr,
            cr=project.cr,
        )
        if missing:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Resonant frequency cannot be calculated.",
                missing_information=missing,
                recommended_action=("Provide valid Lr and Cr values with units.",),
                evidence=(input_evidence,),
            )
        try:
            result = calculate_fr(lr=project.lr, cr=project.cr)
        except EngineeringCalculationError:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Resonant frequency cannot be calculated from the supplied values.",
                missing_information=("valid_lr", "valid_cr"),
                recommended_action=("Correct Lr and Cr values or units.",),
                evidence=(input_evidence,),
            )

        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=Severity.INFO,
            title=self.title,
            description="Resonant frequency was calculated deterministically.",
            evidence=(input_evidence, calculation_evidence(result, "Calculated resonant frequency.")),
            calculated_values={"fr": result},
            requires_engineer_confirmation=False,
        )


class LowerResonantFrequencyCalculationRule(ReviewRule):
    rule_id = "LLC-R006"
    category = "resonant_tank"
    title = "Lower resonant frequency calculation"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        project = context.project
        supplied = {"lr": project.lr, "lm": project.lm, "cr": project.cr}
        missing = tuple(name for name, value in supplied.items() if value is None)
        input_evidence = user_input_evidence(
            "Resonant tank inputs supplied for fp calculation.", **supplied
        )
        if missing:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Lower resonant frequency cannot be calculated.",
                missing_information=missing,
                recommended_action=("Provide valid Lr, Lm, and Cr values with units.",),
                evidence=(input_evidence,),
            )
        try:
            result = calculate_fp(lr=project.lr, lm=project.lm, cr=project.cr)
        except EngineeringCalculationError:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Lower resonant frequency cannot be calculated from the supplied values.",
                missing_information=("valid_lr", "valid_lm", "valid_cr"),
                recommended_action=("Correct Lr, Lm, and Cr values or units.",),
                evidence=(input_evidence,),
            )

        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=Severity.INFO,
            title=self.title,
            description="Lower resonant frequency was calculated using the project-defined fp formula.",
            evidence=(input_evidence, calculation_evidence(result, "Calculated lower resonant frequency.")),
            calculated_values={"fp": result},
            requires_engineer_confirmation=False,
        )


class ResonantFrequencyOperatingRangeRule(ReviewRule):
    rule_id = "LLC-R007"
    category = "resonant_tank"
    title = "Resonant frequency operating range"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        project = context.project
        supplied = {
            "lr": project.lr,
            "cr": project.cr,
            "fsw_min": project.fsw_min,
            "fsw_max": project.fsw_max,
        }
        missing = tuple(name for name, value in supplied.items() if value is None)
        input_evidence = user_input_evidence(
            "Resonant tank and switching range supplied for R007.", **supplied
        )
        if missing:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="The resonant frequency operating range cannot be evaluated.",
                missing_information=missing,
                recommended_action=("Provide Lr, Cr, Fsw Min, and Fsw Max.",),
                evidence=(input_evidence,),
            )
        try:
            fr = calculate_fr(lr=project.lr, cr=project.cr)
            fsw_min = normalize_positive_quantity(
                name="fsw_min", quantity=project.fsw_min, target_unit="Hz"
            )
            fsw_max = normalize_positive_quantity(
                name="fsw_max", quantity=project.fsw_max, target_unit="Hz"
            )
        except EngineeringCalculationError:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="The operating range contains invalid values or units.",
                missing_information=("valid_resonant_tank_and_frequency_range",),
                recommended_action=("Correct the resonant tank and frequency inputs.",),
                evidence=(input_evidence,),
            )

        rule_evidence = rule_definition_evidence(
            self.rule_id,
            "R007 checks the strict relationship Fsw Min < fr < Fsw Max.",
        )
        calculation = calculation_evidence(fr, "Calculated fr used by R007.")
        if fsw_min.value < fr.value < fsw_max.value:
            severity = Severity.PASS
            description = "The calculated resonant frequency lies strictly inside the configured switching range."
            action: tuple[str, ...] = ()
        else:
            severity = Severity.WARNING
            description = "The calculated resonant frequency is not strictly inside the configured switching range."
            action = (
                "Review the intended operating range and resonant tank inputs; this warning does not by itself declare design failure.",
            )

        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=severity,
            title=self.title,
            description=description,
            evidence=(input_evidence, calculation, rule_evidence),
            calculated_values={"fr": fr},
            recommended_action=action,
            requires_engineer_confirmation=False,
        )


class InductanceRatioObservationRule(ReviewRule):
    rule_id = "LLC-R008"
    category = "resonant_tank"
    title = "Lm/Lr ratio observation"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        project = context.project
        missing = tuple(
            name for name, value in {"lr": project.lr, "lm": project.lm}.items() if value is None
        )
        input_evidence = user_input_evidence(
            "Inductances supplied for Lm/Lr observation.", lr=project.lr, lm=project.lm
        )
        if missing:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Lm/Lr cannot be calculated.",
                missing_information=missing,
                recommended_action=("Provide valid Lr and Lm values with units.",),
                evidence=(input_evidence,),
            )
        try:
            result = calculate_lm_lr_ratio(lr=project.lr, lm=project.lm)
        except EngineeringCalculationError:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Lm/Lr cannot be calculated from the supplied values.",
                missing_information=("valid_lr", "valid_lm"),
                recommended_action=("Correct Lr and Lm values or units.",),
                evidence=(input_evidence,),
            )

        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=Severity.INFO,
            title=self.title,
            description="Lm/Lr is reported as an observation only; no universal acceptance range is applied.",
            evidence=(
                input_evidence,
                calculation_evidence(result, "Calculated Lm/Lr ratio."),
                rule_definition_evidence(
                    self.rule_id, "R008 does not define a fixed PASS/FAIL threshold."
                ),
            ),
            calculated_values={"lm_lr_ratio": result},
            requires_engineer_confirmation=False,
        )


class CharacteristicImpedanceRule(ReviewRule):
    rule_id = "LLC-R009"
    category = "resonant_tank"
    title = "Characteristic impedance"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        project = context.project
        missing = tuple(
            name for name, value in {"lr": project.lr, "cr": project.cr}.items() if value is None
        )
        input_evidence = user_input_evidence(
            "Resonant tank inputs supplied for Zr calculation.", lr=project.lr, cr=project.cr
        )
        if missing:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Characteristic impedance cannot be calculated.",
                missing_information=missing,
                recommended_action=("Provide valid Lr and Cr values with units.",),
                evidence=(input_evidence,),
            )
        try:
            result = calculate_zr(lr=project.lr, cr=project.cr)
        except EngineeringCalculationError:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Characteristic impedance cannot be calculated from the supplied values.",
                missing_information=("valid_lr", "valid_cr"),
                recommended_action=("Correct Lr and Cr values or units.",),
                evidence=(input_evidence,),
            )

        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=Severity.INFO,
            title=self.title,
            description="Characteristic impedance was calculated and reported as engineering data.",
            evidence=(input_evidence, calculation_evidence(result, "Calculated characteristic impedance.")),
            calculated_values={"zr": result},
            requires_engineer_confirmation=False,
        )


class OutputPowerConsistencyRule(ReviewRule):
    rule_id = "LLC-R010"
    category = "power_consistency"
    title = "Output power consistency"
    power_formula_version = "LLC-R010-POWER-V1"
    error_formula_version = "LLC-R010-REL-ERROR-V1"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        project = context.project
        supplied = {"pout": project.pout, "vout": project.vout, "iout": project.iout}
        missing = [name for name, value in supplied.items() if value is None]
        tolerance = context.settings.output_power_relative_tolerance
        if tolerance is None:
            missing.append("settings.output_power_relative_tolerance")
        input_evidence = user_input_evidence(
            "Output power, voltage, and current supplied for consistency review.", **supplied
        )
        if missing:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Output power consistency cannot be evaluated without all inputs and a configured tolerance.",
                missing_information=tuple(missing),
                recommended_action=(
                    "Provide Pout, Vout, Iout, and an explicit project output-power relative tolerance.",
                ),
                evidence=(input_evidence,),
            )

        try:
            pout = normalize_positive_quantity(
                name="pout", quantity=project.pout, target_unit="W"
            )
            vout = normalize_positive_quantity(
                name="vout", quantity=project.vout, target_unit="V"
            )
            iout = normalize_positive_quantity(
                name="iout", quantity=project.iout, target_unit="A"
            )
        except EngineeringCalculationError:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Output power consistency inputs contain invalid values or units.",
                missing_information=("valid_pout", "valid_vout", "valid_iout"),
                recommended_action=("Correct Pout, Vout, and Iout values or units.",),
                evidence=(input_evidence,),
            )

        derived_power_value = vout.value * iout.value
        relative_error_value = abs(derived_power_value - pout.value) / pout.value
        derived_power = CalculationResult(
            name="output_power_from_vout_iout",
            value=derived_power_value,
            unit="W",
            inputs={"vout": vout, "iout": iout},
            formula_version=self.power_formula_version,
        )
        relative_error = CalculationResult(
            name="output_power_relative_error",
            value=relative_error_value,
            unit="dimensionless",
            inputs={
                "declared_pout": pout,
                "derived_pout": EngineeringQuantity(value=derived_power_value, unit="W"),
            },
            formula_version=self.error_formula_version,
        )
        tolerance_quantity = EngineeringQuantity(value=tolerance, unit="dimensionless")
        rule_evidence = rule_definition_evidence(
            self.rule_id,
            "R010 compares abs(Vout*Iout-Pout)/Pout with the configured relative tolerance.",
            values={"configured_relative_tolerance": tolerance_quantity},
        )
        calculation = calculation_evidence(
            relative_error, "Calculated output power consistency relative error."
        )
        if relative_error_value <= tolerance:
            severity = Severity.PASS
            description = "Vout × Iout is consistent with Pout within the configured project tolerance."
            action: tuple[str, ...] = ()
        else:
            severity = Severity.WARNING
            description = "Vout × Iout differs from Pout by more than the configured project tolerance."
            action = ("Confirm that Pout, Vout, and Iout describe the same operating point.",)

        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=severity,
            title=self.title,
            description=description,
            evidence=(input_evidence, calculation, rule_evidence),
            calculated_values={
                "output_power_from_vout_iout": derived_power,
                "output_power_relative_error": relative_error,
            },
            recommended_action=action,
            requires_engineer_confirmation=False,
        )

