from collections.abc import Sequence

from app.engine.exceptions import EngineeringCalculationError
from app.engine.units import normalize_positive_quantity
from app.rules.base import ReviewRule
from app.rules.helpers import (
    calculation_evidence,
    insufficient_finding,
    rule_definition_evidence,
    user_input_evidence,
    user_measurement_evidence,
)
from app.schemas.engineering import CalculationResult, EngineeringQuantity
from app.schemas.review import Finding, ReviewContext, Severity


class MOSFETStaticVoltageScreeningRule(ReviewRule):
    rule_id = "LLC-R011"
    category = "primary_switch"
    title = "MOSFET static voltage screening"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        rating = context.mosfet.vds_rating
        vin_max = context.project.vin_max
        supplied = {"mosfet_vds_rating": rating, "vin_max": vin_max}
        missing = tuple(name for name, value in supplied.items() if value is None)
        evidence = (
            user_input_evidence(
                "User-provided MOSFET rating and maximum bus voltage.", **supplied
            ),
            rule_definition_evidence(
                self.rule_id,
                "R011 compares MOSFET VDS rating with Vin Max as a static screen only.",
            ),
        )
        if missing:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="MOSFET static voltage screening cannot be completed.",
                missing_information=missing,
                recommended_action=("Provide MOSFET VDS rating and Vin Max with units.",),
                evidence=evidence,
            )
        assert rating is not None
        assert vin_max is not None
        try:
            normalized_rating = normalize_positive_quantity(
                name="mosfet_vds_rating", quantity=rating, target_unit="V"
            )
            normalized_vin_max = normalize_positive_quantity(
                name="vin_max", quantity=vin_max, target_unit="V"
            )
        except EngineeringCalculationError:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="MOSFET voltage screening inputs contain invalid values or units.",
                missing_information=("valid_mosfet_vds_rating", "valid_vin_max"),
                recommended_action=("Correct the rating and bus voltage data.",),
                evidence=evidence,
            )

        if normalized_rating.value <= normalized_vin_max.value:
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=Severity.CRITICAL,
                title=self.title,
                description="MOSFET VDS rating is less than or equal to Vin Max.",
                evidence=evidence,
                recommended_action=(
                    "Do not treat this device as statically adequate; select or verify a rating above Vin Max.",
                ),
                requires_engineer_confirmation=True,
            )

        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=Severity.PASS,
            title=self.title,
            description=(
                "Static screening passed. This does not establish MOSFET voltage safety because "
                "overshoot, ringing, parasitic inductance, and transient conditions are not included."
            ),
            evidence=evidence,
            requires_engineer_confirmation=False,
        )


class MOSFETMeasuredPeakVoltageRule(ReviewRule):
    rule_id = "LLC-R012"
    category = "primary_switch"
    title = "MOSFET measured peak voltage"
    margin_formula_version = "LLC-R012-VDS-MARGIN-V1"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        rating = context.mosfet.vds_rating
        measured_peak = context.mosfet.measured_vds_peak
        supplied = {"mosfet_vds_rating": rating, "measured_vds_peak": measured_peak}
        missing = tuple(name for name, value in supplied.items() if value is None)
        input_evidence = user_measurement_evidence(
            "User-provided MOSFET VDS rating and measured peak voltage.",
            ("measured_vds_peak",),
            **supplied,
        )
        if missing:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Measured MOSFET peak voltage screening cannot be completed.",
                missing_information=missing,
                recommended_action=("Provide MOSFET VDS rating and measured VDS peak with units.",),
                evidence=(input_evidence,),
            )
        assert rating is not None
        assert measured_peak is not None
        try:
            normalized_rating = normalize_positive_quantity(
                name="mosfet_vds_rating", quantity=rating, target_unit="V"
            )
            normalized_peak = normalize_positive_quantity(
                name="measured_vds_peak", quantity=measured_peak, target_unit="V"
            )
        except EngineeringCalculationError:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="MOSFET peak voltage inputs contain invalid values or units.",
                missing_information=("valid_mosfet_vds_rating", "valid_measured_vds_peak"),
                recommended_action=("Correct the VDS rating and measured peak data.",),
                evidence=(input_evidence,),
            )

        margin_value = (normalized_rating.value - normalized_peak.value) / normalized_rating.value
        margin = CalculationResult(
            name="measured_vds_margin_ratio",
            value=margin_value,
            unit="dimensionless",
            inputs={"vds_rating": normalized_rating, "measured_vds_peak": normalized_peak},
            formula_version=self.margin_formula_version,
        )
        calculation = calculation_evidence(
            margin, "Calculated relative margin from measured peak to VDS rating."
        )
        rule_evidence = rule_definition_evidence(
            self.rule_id,
            "R012 treats measured peak above the absolute VDS rating as CRITICAL; any additional margin requirement must be configured.",
        )

        if normalized_peak.value > normalized_rating.value:
            severity = Severity.CRITICAL
            description = "Measured VDS peak exceeds the supplied MOSFET absolute VDS rating."
            action: tuple[str, ...] = (
                "Stop using this result as an acceptable operating condition and require qualified engineer review of the device stress and measurement setup.",
            )
            requires_confirmation = True
            missing_information: tuple[str, ...] = ()
        else:
            required_margin = context.settings.measured_vds_required_margin_ratio
            if required_margin is None:
                severity = Severity.INFO
                description = (
                    "Measured VDS peak does not exceed the supplied rating, but no project margin "
                    "requirement is configured; only the absolute-rating comparison was performed."
                )
                action = ("Configure a project-approved measured VDS margin if margin review is required.",)
                requires_confirmation = False
                missing_information = ("settings.measured_vds_required_margin_ratio",)
            elif margin_value < required_margin:
                severity = Severity.WARNING
                description = "Measured VDS margin is below the configured project requirement."
                action = ("Review the measured waveform, operating conditions, and configured margin requirement.",)
                requires_confirmation = True
                missing_information = ()
                rule_evidence = rule_definition_evidence(
                    self.rule_id,
                    "R012 configured measured VDS margin requirement.",
                    values={
                        "required_margin_ratio": EngineeringQuantity(
                            value=required_margin, unit="dimensionless"
                        )
                    },
                )
            else:
                severity = Severity.PASS
                description = "Measured VDS margin meets the configured project requirement."
                action = ()
                requires_confirmation = False
                missing_information = ()
                rule_evidence = rule_definition_evidence(
                    self.rule_id,
                    "R012 configured measured VDS margin requirement.",
                    values={
                        "required_margin_ratio": EngineeringQuantity(
                            value=required_margin, unit="dimensionless"
                        )
                    },
                )

        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=severity,
            title=self.title,
            description=description,
            evidence=(input_evidence, calculation, rule_evidence),
            calculated_values={"measured_vds_margin_ratio": margin},
            missing_information=missing_information,
            recommended_action=action,
            requires_engineer_confirmation=requires_confirmation,
        )


class MOSFETCurrentScreeningRule(ReviewRule):
    rule_id = "LLC-R013"
    category = "primary_switch"
    title = "MOSFET current screening"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        measured = context.mosfet.measured_peak_current
        rating = context.mosfet.current_rating
        condition = context.mosfet.current_temperature_condition
        missing = []
        if measured is None:
            missing.append("mosfet.measured_peak_current")
        if rating is None:
            missing.append("mosfet.current_rating")
        if condition is None:
            missing.append("mosfet.current_temperature_condition")
        evidence = (
            user_measurement_evidence(
                "User-provided MOSFET current data. Temperature condition: "
                + (condition or "not provided"),
                ("measured_peak_current",),
                measured_peak_current=measured,
                current_rating=rating,
            ),
            rule_definition_evidence(
                self.rule_id,
                "R013 requires measured peak current, device current rating, and a temperature condition.",
            ),
        )
        if missing:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="MOSFET current screening cannot be completed with comparable conditions.",
                missing_information=tuple(missing),
                recommended_action=("Provide measured peak current, rating, and temperature condition.",),
                evidence=evidence,
            )
        assert measured is not None
        assert rating is not None
        try:
            normalized_measured = normalize_positive_quantity(
                name="measured_peak_current", quantity=measured, target_unit="A"
            )
            normalized_rating = normalize_positive_quantity(
                name="mosfet_current_rating", quantity=rating, target_unit="A"
            )
        except EngineeringCalculationError:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="MOSFET current inputs contain invalid values or units.",
                missing_information=("valid_measured_peak_current", "valid_current_rating"),
                recommended_action=("Correct the current values and units.",),
                evidence=evidence,
            )

        if normalized_measured.value > normalized_rating.value:
            severity = Severity.CRITICAL
            description = "Measured peak current exceeds the supplied device current rating."
            action: tuple[str, ...] = (
                "Require engineer review of current stress, rating conditions, and thermal conditions.",
            )
            requires_confirmation = True
        else:
            severity = Severity.INFO
            description = (
                "Measured peak current does not exceed the supplied rating under the documented "
                "temperature condition; this is not a complete current-safety conclusion."
            )
            action = ()
            requires_confirmation = False

        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=severity,
            title=self.title,
            description=description,
            evidence=evidence,
            recommended_action=action,
            requires_engineer_confirmation=requires_confirmation,
        )


class ResonantCapacitorVoltageRatingRule(ReviewRule):
    rule_id = "LLC-R014"
    category = "resonant_capacitor"
    title = "Resonant capacitor voltage rating"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        rating = context.resonant_capacitor.voltage_rating
        stress = context.resonant_capacitor.voltage_stress
        supplied = {"capacitor_voltage_rating": rating, "capacitor_voltage_stress": stress}
        missing = tuple(name for name, value in supplied.items() if value is None)
        evidence = (
            user_measurement_evidence(
                "User-provided resonant capacitor voltage data.",
                ("capacitor_voltage_stress",),
                **supplied,
            ),
            rule_definition_evidence(
                self.rule_id, "R014 compares supplied voltage stress with voltage rating."
            ),
        )
        if missing:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Resonant capacitor voltage screening cannot be completed.",
                missing_information=missing,
                recommended_action=("Provide capacitor voltage rating and measured or calculated stress.",),
                evidence=evidence,
            )
        assert rating is not None
        assert stress is not None
        try:
            normalized_rating = normalize_positive_quantity(
                name="capacitor_voltage_rating", quantity=rating, target_unit="V"
            )
            normalized_stress = normalize_positive_quantity(
                name="capacitor_voltage_stress", quantity=stress, target_unit="V"
            )
        except EngineeringCalculationError:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Capacitor voltage inputs contain invalid values or units.",
                missing_information=("valid_voltage_rating", "valid_voltage_stress"),
                recommended_action=("Correct the capacitor voltage values and units.",),
                evidence=evidence,
            )

        if normalized_stress.value > normalized_rating.value:
            severity = Severity.CRITICAL
            description = "Supplied resonant capacitor voltage stress exceeds its supplied rating."
            action: tuple[str, ...] = (
                "Require engineer review of the stress evidence and capacitor selection.",
            )
            requires_confirmation = True
        else:
            severity = Severity.INFO
            description = (
                "Supplied voltage stress does not exceed the supplied rating; no project voltage "
                "margin requirement was applied and this is not a safety conclusion."
            )
            action = ()
            requires_confirmation = False

        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=severity,
            title=self.title,
            description=description,
            evidence=evidence,
            recommended_action=action,
            requires_engineer_confirmation=requires_confirmation,
        )


class ResonantCapacitorRMSCurrentRule(ReviewRule):
    rule_id = "LLC-R015"
    category = "resonant_capacitor"
    title = "Resonant capacitor RMS current"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        rating = context.resonant_capacitor.rms_current_rating
        stress = context.resonant_capacitor.rms_current_stress
        supplied = {"capacitor_rms_current_rating": rating, "capacitor_rms_current_stress": stress}
        missing = tuple(name for name, value in supplied.items() if value is None)
        evidence = (
            user_measurement_evidence(
                "User-provided resonant capacitor RMS current data.",
                ("capacitor_rms_current_stress",),
                **supplied,
            ),
            rule_definition_evidence(
                self.rule_id, "R015 compares supplied RMS current stress with RMS current rating."
            ),
        )
        if missing:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Resonant capacitor RMS current screening cannot be completed.",
                missing_information=missing,
                recommended_action=("Provide capacitor RMS rating and measured or calculated RMS current.",),
                evidence=evidence,
            )
        assert rating is not None
        assert stress is not None
        try:
            normalized_rating = normalize_positive_quantity(
                name="capacitor_rms_current_rating", quantity=rating, target_unit="A"
            )
            normalized_stress = normalize_positive_quantity(
                name="capacitor_rms_current_stress", quantity=stress, target_unit="A"
            )
        except EngineeringCalculationError:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Capacitor RMS current inputs contain invalid values or units.",
                missing_information=("valid_rms_current_rating", "valid_rms_current_stress"),
                recommended_action=("Correct the capacitor RMS current values and units.",),
                evidence=evidence,
            )

        if normalized_stress.value > normalized_rating.value:
            severity = Severity.CRITICAL
            description = "Supplied resonant capacitor RMS current stress exceeds its supplied rating."
            action: tuple[str, ...] = (
                "Require engineer review of RMS stress, rating conditions, and capacitor selection.",
            )
            requires_confirmation = True
        else:
            severity = Severity.INFO
            description = (
                "Supplied RMS current stress does not exceed the supplied rating; no project current "
                "margin requirement was applied and this is not a thermal or lifetime conclusion."
            )
            action = ()
            requires_confirmation = False

        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=severity,
            title=self.title,
            description=description,
            evidence=evidence,
            recommended_action=action,
            requires_engineer_confirmation=requires_confirmation,
        )


class ControllerFrequencyCapabilityRule(ReviewRule):
    rule_id = "LLC-R016"
    category = "control"
    title = "Controller frequency capability"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        supplied = {
            "project_fsw_min": context.project.fsw_min,
            "project_fsw_max": context.project.fsw_max,
            "controller_frequency_min": context.controller.frequency_min,
            "controller_frequency_max": context.controller.frequency_max,
        }
        missing = tuple(name for name, value in supplied.items() if value is None)
        evidence = (
            user_input_evidence("Project and controller frequency ranges.", **supplied),
            rule_definition_evidence(
                self.rule_id,
                "R016 requires the controller range to cover the complete configured project switching range.",
            ),
        )
        if missing:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Controller frequency capability cannot be evaluated.",
                missing_information=missing,
                recommended_action=("Provide project and controller minimum and maximum frequencies.",),
                evidence=evidence,
            )
        assert context.project.fsw_min is not None
        assert context.project.fsw_max is not None
        assert context.controller.frequency_min is not None
        assert context.controller.frequency_max is not None
        try:
            project_min = normalize_positive_quantity(
                name="project_fsw_min", quantity=context.project.fsw_min, target_unit="Hz"
            )
            project_max = normalize_positive_quantity(
                name="project_fsw_max", quantity=context.project.fsw_max, target_unit="Hz"
            )
            controller_min = normalize_positive_quantity(
                name="controller_frequency_min",
                quantity=context.controller.frequency_min,
                target_unit="Hz",
            )
            controller_max = normalize_positive_quantity(
                name="controller_frequency_max",
                quantity=context.controller.frequency_max,
                target_unit="Hz",
            )
        except EngineeringCalculationError:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Controller frequency inputs contain invalid values or units.",
                missing_information=("valid_project_and_controller_frequency_ranges",),
                recommended_action=("Correct the frequency values and units.",),
                evidence=evidence,
            )

        if project_min.value >= project_max.value or controller_min.value >= controller_max.value:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="One of the supplied frequency ranges is not strictly ordered.",
                missing_information=("ordered_project_and_controller_frequency_ranges",),
                recommended_action=("Correct both minimum-to-maximum frequency definitions.",),
                evidence=evidence,
            )

        if controller_min.value <= project_min.value and controller_max.value >= project_max.value:
            severity = Severity.PASS
            description = "The supplied controller frequency range covers the project switching range."
            action: tuple[str, ...] = ()
        else:
            severity = Severity.WARNING
            description = "The supplied controller frequency range does not cover the complete project switching range."
            action = ("Review controller selection or the configured project switching range.",)

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
