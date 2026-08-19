from collections.abc import Sequence
from functools import lru_cache

from app.engine.exceptions import EngineeringCalculationError
from app.engine.operating_envelope import calculate_operating_envelope
from app.engine.units import normalize_positive_quantity, normalize_transformer_ratio
from app.rules.base import ReviewRule
from app.rules.helpers import (
    calculation_evidence,
    insufficient_finding,
    rule_definition_evidence,
    user_input_evidence,
)
from app.schemas.engineering import (
    CalculationResult,
    EngineeringQuantity,
    OperatingEnvelopeResult,
)
from app.schemas.review import EvidenceItem, Finding, ReviewContext, Severity

GAIN_MODEL_PARAMETER_UNITS = {
    "lr": "H",
    "lm": "H",
    "cr": "F",
    "vin_min": "V",
    "vin_nom": "V",
    "vin_max": "V",
    "vout": "V",
    "pout": "W",
    "transformer_ratio": "dimensionless",
    "fsw_min": "Hz",
    "fsw_max": "Hz",
}


def _supplied_parameters(
    context: ReviewContext,
) -> dict[str, EngineeringQuantity | None]:
    project = context.project
    return {
        name: getattr(project, name) for name in GAIN_MODEL_PARAMETER_UNITS
    }


def _gain_rule_evidence(
    rule_id: str,
    context: ReviewContext,
    description: str,
) -> tuple[EvidenceItem, ...]:
    return (
        user_input_evidence(
            "FHA 增益模型使用的用户输入。",
            **_supplied_parameters(context),
        ),
        rule_definition_evidence(rule_id, description),
    )


def _missing_parameters(context: ReviewContext) -> tuple[str, ...]:
    return tuple(
        name
        for name, value in _supplied_parameters(context).items()
        if value is None
    )


def _validate_gain_parameters(context: ReviewContext) -> None:
    supplied = _supplied_parameters(context)
    for name, target_unit in GAIN_MODEL_PARAMETER_UNITS.items():
        value = supplied[name]
        assert value is not None
        if name == "transformer_ratio":
            normalize_transformer_ratio(value)
        else:
            normalize_positive_quantity(
                name=name,
                quantity=value,
                target_unit=target_unit,
            )
    fsw_min_input = supplied["fsw_min"]
    fsw_max_input = supplied["fsw_max"]
    assert fsw_min_input is not None
    assert fsw_max_input is not None
    fsw_min = normalize_positive_quantity(
        name="fsw_min",
        quantity=fsw_min_input,
        target_unit="Hz",
    )
    fsw_max = normalize_positive_quantity(
        name="fsw_max",
        quantity=fsw_max_input,
        target_unit="Hz",
    )
    if fsw_min.value > fsw_max.value:
        raise EngineeringCalculationError("fsw_min must not be greater than fsw_max")


@lru_cache(maxsize=128)
def _cached_operating_envelope(
    key: tuple[tuple[str, float, str], ...],
) -> OperatingEnvelopeResult:
    values = {
        name: EngineeringQuantity(value=value, unit=unit)
        for name, value, unit in key
    }
    return calculate_operating_envelope(
        lr=values["lr"],
        lm=values["lm"],
        cr=values["cr"],
        vin_min=values["vin_min"],
        vin_nom=values["vin_nom"],
        vin_max=values["vin_max"],
        vout=values["vout"],
        pout=values["pout"],
        transformer_ratio=values["transformer_ratio"],
        fsw_min=values["fsw_min"],
        fsw_max=values["fsw_max"],
    )


def _get_envelope(
    context: ReviewContext,
) -> tuple[OperatingEnvelopeResult | None, tuple[str, ...]]:
    missing = _missing_parameters(context)
    if missing:
        return None, missing
    try:
        _validate_gain_parameters(context)
        project = context.project
        assert project.lr is not None
        assert project.lm is not None
        assert project.cr is not None
        assert project.vin_min is not None
        assert project.vin_nom is not None
        assert project.vin_max is not None
        assert project.vout is not None
        assert project.pout is not None
        assert project.transformer_ratio is not None
        assert project.fsw_min is not None
        assert project.fsw_max is not None
        key = tuple(
            (name, value.value, value.unit)
            for name, value in _supplied_parameters(context).items()
            if value is not None
        )
        return _cached_operating_envelope(key), ()
    except EngineeringCalculationError:
        return None, ("valid_fha_operating_envelope",)


def _not_requested(
    *, rule_id: str, category: str, title: str, context: ReviewContext, description: str
) -> Finding | None:
    if context.requests.full_gain_review_requested:
        return None
    return Finding(
        rule_id=rule_id,
        category=category,
        severity=Severity.INFO,
        title=title,
        description=description,
        evidence=(rule_definition_evidence(rule_id, description),),
        requires_engineer_confirmation=False,
    )


class GainModelPrerequisitesRule(ReviewRule):
    rule_id = "LLC-R021"
    category = "fha_gain"
    title = "FHA gain model prerequisites"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        not_requested = _not_requested(
            rule_id=self.rule_id,
            category=self.category,
            title=self.title,
            context=context,
            description="Full gain review is not requested, so FHA model prerequisites are not evaluated.",
        )
        if not_requested is not None:
            return not_requested
        evidence = _gain_rule_evidence(
            self.rule_id,
            context,
            "R021 requires the complete FHA operating-envelope input set.",
        )
        missing = _missing_parameters(context)
        if missing:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="FHA gain model prerequisites are incomplete.",
                missing_information=missing,
                recommended_action=("Provide every FHA gain model input with an explicit unit.",),
                evidence=evidence,
            )
        try:
            _validate_gain_parameters(context)
        except EngineeringCalculationError:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="FHA gain model prerequisites contain invalid values or units.",
                missing_information=("valid_fha_gain_model_inputs",),
                recommended_action=("Correct the FHA input values, units, or frequency range.",),
                evidence=evidence,
            )
        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=Severity.PASS,
            title=self.title,
            description="All FHA gain model prerequisites are available and dimensionally valid.",
            evidence=evidence,
            requires_engineer_confirmation=False,
        )


class RequiredGainCoverageRule(ReviewRule):
    rule_id = "LLC-R022"
    category = "fha_gain"
    title = "Required gain coverage"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        not_requested = _not_requested(
            rule_id=self.rule_id,
            category=self.category,
            title=self.title,
            context=context,
            description="Full gain review is not requested, so required-gain coverage is not evaluated.",
        )
        if not_requested is not None:
            return not_requested
        envelope, missing = _get_envelope(context)
        evidence = _gain_rule_evidence(
            self.rule_id,
            context,
            "R022 compares available maximum FHA gain with the maximum required gain at Vin Min.",
        )
        if envelope is None:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="Required-gain coverage cannot be evaluated.",
                missing_information=missing,
                recommended_action=("Complete and correct the FHA gain model inputs.",),
                evidence=evidence,
            )
        evidence = (
            *evidence,
            calculation_evidence(envelope.available_gain_max, "Available FHA maximum gain."),
            calculation_evidence(
                envelope.required_gain_at_vin_min,
                "Maximum required gain at Vin Min.",
            ),
        )
        covered = envelope.available_gain_max.value >= envelope.required_gain_at_vin_min.value
        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=Severity.PASS if covered else Severity.WARNING,
            title=self.title,
            description=(
                "Available FHA gain covers the maximum required gain in the scanned frequency range."
                if covered
                else "Available FHA gain does not cover the maximum required gain in the scanned frequency range."
            ),
            evidence=evidence,
            calculated_values={
                "available_gain_max": envelope.available_gain_max,
                "required_gain_at_vin_min": envelope.required_gain_at_vin_min,
                "available_gain_frequency": envelope.available_gain_frequency,
            },
            recommended_action=(
                ()
                if covered
                else ("Review the resonant tank, transformer ratio, and configured frequency range.",)
            ),
            requires_engineer_confirmation=False,
        )


class OperatingPointRegionRule(ReviewRule):
    rule_id = "LLC-R023"
    category = "fha_gain"
    title = "Operating point region"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        not_requested = _not_requested(
            rule_id=self.rule_id,
            category=self.category,
            title=self.title,
            context=context,
            description="Full gain review is not requested, so the FHA operating-point region is not evaluated.",
        )
        if not_requested is not None:
            return not_requested
        envelope, missing = _get_envelope(context)
        evidence = _gain_rule_evidence(
            self.rule_id,
            context,
            "R023 evaluates the nominal FHA operating-point region from Im(Zin).",
        )
        if envelope is None:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="The nominal FHA operating-point region cannot be evaluated.",
                missing_information=missing,
                recommended_action=("Complete and correct the FHA gain model inputs.",),
                evidence=evidence,
            )
        nominal = envelope.operating_points["vin_nom"]
        evidence = (*evidence, calculation_evidence(envelope.required_gain_at_vin_nom, "Nominal required gain."))
        if nominal.status == "VALID":
            assert nominal.operating_region == "INDUCTIVE"
            assert nominal.tank_gain is not None
            assert nominal.switching_frequency is not None
            assert nominal.input_impedance is not None
            evidence = (
                *evidence,
                calculation_evidence(nominal.tank_gain, "Nominal FHA tank gain."),
            )
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=Severity.PASS,
                title=self.title,
                description="The nominal FHA operating point is in the inductive region.",
                evidence=evidence,
                calculated_values={
                    "nominal_tank_gain": nominal.tank_gain,
                    "switching_frequency": nominal.switching_frequency,
                    "input_impedance_imaginary": EngineeringQuantity(
                        value=nominal.input_impedance.imaginary,
                        unit="ohm",
                    ),
                },
                requires_engineer_confirmation=False,
            )
        capacitive = next(
            (candidate for candidate in nominal.candidates if candidate.operating_region == "CAPACITIVE"),
            None,
        )
        if capacitive is not None:
            evidence = (*evidence, calculation_evidence(capacitive.tank_gain, "Nominal capacitive FHA root."))
            return Finding(
                rule_id=self.rule_id,
                category=self.category,
                severity=Severity.WARNING,
                title=self.title,
                description="The nominal FHA operating point is capacitive and requires engineer review; this does not prove ZVS failure.",
                evidence=evidence,
                calculated_values={
                    "operating_region_gain": capacitive.tank_gain,
                    "switching_frequency": capacitive.switching_frequency,
                },
                recommended_action=("Review the nominal operating point and measured switching behavior.",),
                requires_engineer_confirmation=False,
            )
        return insufficient_finding(
            rule_id=self.rule_id,
            category=self.category,
            title=self.title,
            description="No nominal FHA operating-point root was found in the configured range.",
            missing_information=("nominal_fha_operating_point",),
            recommended_action=("Review the required gain and configured switching-frequency range.",),
            evidence=evidence,
        )


class FrequencyCapabilityRule(ReviewRule):
    rule_id = "LLC-R024"
    category = "fha_gain"
    title = "Operating frequency capability"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        not_requested = _not_requested(
            rule_id=self.rule_id,
            category=self.category,
            title=self.title,
            context=context,
            description="Full gain review is not requested, so FHA frequency capability is not evaluated.",
        )
        if not_requested is not None:
            return not_requested
        envelope, missing = _get_envelope(context)
        evidence = _gain_rule_evidence(
            self.rule_id,
            context,
            "R024 checks that the nominal FHA operating point is inside the configured switching-frequency range.",
        )
        if envelope is None:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="FHA frequency capability cannot be evaluated.",
                missing_information=missing,
                recommended_action=("Complete and correct the FHA gain model inputs.",),
                evidence=evidence,
            )
        nominal = envelope.operating_points["vin_nom"]
        selected_frequency = nominal.switching_frequency
        if nominal.status == "VALID":
            assert selected_frequency is not None
            frequency = selected_frequency.value
            in_range = envelope.frequency_min.value <= frequency <= envelope.frequency_max.value
        else:
            in_range = False
            frequency = None
        calculated_values: dict[str, CalculationResult | EngineeringQuantity] = {
            "fsw_min": envelope.frequency_min,
            "fsw_max": envelope.frequency_max,
        }
        if selected_frequency is not None:
            calculated_values["switching_frequency"] = selected_frequency
        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=Severity.PASS if in_range else Severity.WARNING,
            title=self.title,
            description=(
                "The nominal FHA operating frequency is inside the configured switching-frequency range."
                if in_range
                else "No valid nominal FHA operating frequency was found inside the configured switching-frequency range."
            ),
            evidence=(
                *evidence,
                rule_definition_evidence(
                    self.rule_id,
                    "R024 requires fsw_min ≤ fs ≤ fsw_max for the calculated operating frequency.",
                ),
            ),
            calculated_values=calculated_values,
            recommended_action=(
                () if in_range else ("Review the tank gain, required gain, and switching-frequency range.",)
            ),
            requires_engineer_confirmation=False,
        )


class GainPeakMarginRule(ReviewRule):
    rule_id = "LLC-R025"
    category = "fha_gain"
    title = "FHA gain peak margin"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        not_requested = _not_requested(
            rule_id=self.rule_id,
            category=self.category,
            title=self.title,
            context=context,
            description="Full gain review is not requested, so FHA gain peak information is not evaluated.",
        )
        if not_requested is not None:
            return not_requested
        envelope, missing = _get_envelope(context)
        evidence = _gain_rule_evidence(
            self.rule_id,
            context,
            "R025 reports FHA peak-gain information without imposing an unconfigured margin threshold.",
        )
        if envelope is None:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="FHA gain peak information cannot be calculated.",
                missing_information=missing,
                recommended_action=("Complete and correct the FHA gain model inputs.",),
                evidence=evidence,
            )
        evidence = (*evidence, calculation_evidence(envelope.available_gain_max, "FHA peak gain."))
        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=Severity.INFO,
            title=self.title,
            description="FHA peak gain is reported for engineering review; no hard-coded gain-margin threshold is applied.",
            evidence=evidence,
            calculated_values={
                "available_gain_max": envelope.available_gain_max,
                "required_gain_at_vin_min": envelope.required_gain_at_vin_min,
                "available_gain_frequency": envelope.available_gain_frequency,
            },
            requires_engineer_confirmation=False,
        )


class FHAApplicabilityRule(ReviewRule):
    rule_id = "LLC-R026"
    category = "fha_gain"
    title = "FHA applicability"

    def evaluate(
        self, context: ReviewContext, prior_findings: Sequence[Finding] = ()
    ) -> Finding:
        not_requested = _not_requested(
            rule_id=self.rule_id,
            category=self.category,
            title=self.title,
            context=context,
            description="Full gain review is not requested, so FHA applicability is not evaluated.",
        )
        if not_requested is not None:
            return not_requested
        envelope, missing = _get_envelope(context)
        evidence = _gain_rule_evidence(
            self.rule_id,
            context,
            "R026 reports the FHA estimate boundary without claiming accuracy away from resonance.",
        )
        if envelope is None:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="FHA applicability cannot be assessed without a valid nominal operating point.",
                missing_information=missing,
                recommended_action=("Complete and correct the FHA gain model inputs.",),
                evidence=evidence,
            )
        nominal = envelope.operating_points["vin_nom"]
        normalized_frequency = nominal.normalized_frequency
        if nominal.status != "VALID" or normalized_frequency is None:
            return insufficient_finding(
                rule_id=self.rule_id,
                category=self.category,
                title=self.title,
                description="FHA applicability cannot be assessed without a valid nominal operating point.",
                missing_information=("nominal_fha_operating_point",),
                recommended_action=("Review the required gain and switching-frequency range.",),
                evidence=evidence,
            )
        evidence = (
            *evidence,
            calculation_evidence(envelope.resonant_frequency, "Resonant frequency used for FHA applicability context."),
            calculation_evidence(normalized_frequency, "Nominal normalized frequency."),
        )
        return Finding(
            rule_id=self.rule_id,
            category=self.category,
            severity=Severity.INFO,
            title=self.title,
            description="FHA estimate; model accuracy may degrade away from resonance and under unmodeled light-load or parasitic conditions.",
            evidence=evidence,
            calculated_values={
                "resonant_frequency": envelope.resonant_frequency,
                "nominal_normalized_frequency": normalized_frequency,
            },
            recommended_action=("Confirm FHA assumptions against measured waveforms and test conditions.",),
            requires_engineer_confirmation=False,
        )
