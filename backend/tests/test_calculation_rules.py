from collections.abc import Callable

import pytest

from app.engine import calculate_output_current
from app.rules.builtin import (
    CharacteristicImpedanceRule,
    InductanceRatioObservationRule,
    LowerResonantFrequencyCalculationRule,
    OutputPowerConsistencyRule,
    ResonantFrequencyCalculationRule,
    ResonantFrequencyOperatingRangeRule,
)
from app.schemas.engineering import EngineeringQuantity
from app.schemas.review import EvidenceSource, ReviewContext, ReviewParameterName, Severity


def q(value: float, unit: str) -> EngineeringQuantity:
    return EngineeringQuantity(value=value, unit=unit)


def test_r005_reports_versioned_resonant_frequency(
    normal_review_context: ReviewContext,
) -> None:
    finding = ResonantFrequencyCalculationRule().evaluate(normal_review_context)
    result = finding.calculated_values["fr"]

    assert finding.severity == Severity.INFO
    assert result.formula_version == "LLC-FR-V1"
    assert result.value == pytest.approx(109_437.19316806001)
    assert finding.evidence


@pytest.mark.parametrize("field", ["lr", "cr"])
def test_r005_handles_missing_and_invalid_inputs(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
    field: str,
) -> None:
    missing = update_review_context(normal_review_context, "project", **{field: None})
    invalid = update_review_context(
        normal_review_context, "project", **{field: q(-1, "H" if field == "lr" else "F")}
    )

    assert ResonantFrequencyCalculationRule().evaluate(missing).severity == Severity.INSUFFICIENT_DATA
    assert ResonantFrequencyCalculationRule().evaluate(invalid).severity == Severity.INSUFFICIENT_DATA


def test_r006_reports_versioned_lower_resonant_frequency(
    normal_review_context: ReviewContext,
) -> None:
    finding = LowerResonantFrequencyCalculationRule().evaluate(normal_review_context)
    result = finding.calculated_values["fp"]

    assert finding.severity == Severity.INFO
    assert result.formula_version == "LLC-FP-V1"
    assert result.value == pytest.approx(39_524.06957654706)


@pytest.mark.parametrize("field", ["lr", "lm", "cr"])
def test_r006_handles_each_missing_input(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
    field: str,
) -> None:
    context = update_review_context(normal_review_context, "project", **{field: None})

    assert LowerResonantFrequencyCalculationRule().evaluate(context).severity == Severity.INSUFFICIENT_DATA


def test_r006_rejects_invalid_inductance_unit(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    context = update_review_context(normal_review_context, "project", lm=q(300, "V"))

    assert LowerResonantFrequencyCalculationRule().evaluate(context).severity == Severity.INSUFFICIENT_DATA


def test_r007_passes_when_fr_is_inside_switching_range(
    normal_review_context: ReviewContext,
) -> None:
    finding = ResonantFrequencyOperatingRangeRule().evaluate(normal_review_context)

    assert finding.severity == Severity.PASS
    assert finding.calculated_values["fr"].formula_version == "LLC-FR-V1"


def test_r007_warns_when_fr_is_outside_switching_range(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    context = update_review_context(
        normal_review_context,
        "project",
        fsw_min=q(120, "kHz"),
        fsw_max=q(180, "kHz"),
    )

    finding = ResonantFrequencyOperatingRangeRule().evaluate(context)

    assert finding.severity == Severity.WARNING
    assert finding.evidence
    assert "does not by itself declare design failure" in finding.recommended_action[0]


def test_r007_handles_missing_and_invalid_inputs(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    missing = update_review_context(normal_review_context, "project", fsw_min=None)
    invalid = update_review_context(normal_review_context, "project", fsw_max=q(150, "V"))

    assert ResonantFrequencyOperatingRangeRule().evaluate(missing).severity == Severity.INSUFFICIENT_DATA
    assert ResonantFrequencyOperatingRangeRule().evaluate(invalid).severity == Severity.INSUFFICIENT_DATA


def test_r008_is_info_only_without_fixed_threshold(
    normal_review_context: ReviewContext,
) -> None:
    finding = InductanceRatioObservationRule().evaluate(normal_review_context)

    assert finding.severity == Severity.INFO
    assert finding.calculated_values["lm_lr_ratio"].value == pytest.approx(300 / 45)
    assert "no universal acceptance range" in finding.description


def test_r008_handles_missing_and_invalid_inputs(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    missing = update_review_context(normal_review_context, "project", lm=None)
    invalid = update_review_context(normal_review_context, "project", lr=q(45, "V"))

    assert InductanceRatioObservationRule().evaluate(missing).severity == Severity.INSUFFICIENT_DATA
    assert InductanceRatioObservationRule().evaluate(invalid).severity == Severity.INSUFFICIENT_DATA


def test_r009_reports_characteristic_impedance_as_info(
    normal_review_context: ReviewContext,
) -> None:
    finding = CharacteristicImpedanceRule().evaluate(normal_review_context)

    assert finding.severity == Severity.INFO
    assert finding.calculated_values["zr"].value == pytest.approx(30.942637387763806)


def test_r009_handles_missing_and_invalid_inputs(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    missing = update_review_context(normal_review_context, "project", cr=None)
    invalid = update_review_context(normal_review_context, "project", cr=q(47, "H"))

    assert CharacteristicImpedanceRule().evaluate(missing).severity == Severity.INSUFFICIENT_DATA
    assert CharacteristicImpedanceRule().evaluate(invalid).severity == Severity.INSUFFICIENT_DATA


def test_r010_passes_at_or_below_configured_tolerance(
    normal_review_context: ReviewContext,
) -> None:
    finding = OutputPowerConsistencyRule().evaluate(normal_review_context)

    assert finding.severity == Severity.PASS
    assert finding.calculated_values["output_power_from_vout_iout"].formula_version == "LLC-R010-POWER-V1"
    assert finding.calculated_values["output_power_relative_error"].value == pytest.approx(0.0)


def test_r010_warns_above_explicit_project_tolerance(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    context = update_review_context(normal_review_context, "project", iout=q(12, "A"))

    finding = OutputPowerConsistencyRule().evaluate(context)

    assert finding.severity == Severity.WARNING
    assert finding.evidence
    assert finding.calculated_values["output_power_relative_error"].value == pytest.approx(0.152)


def test_r010_preserves_calculation_provenance_for_derived_iout(
    normal_review_context: ReviewContext,
) -> None:
    project = normal_review_context.project.model_copy(update={"iout": None})
    iout_result = calculate_output_current(
        pout=project.pout,
        vout=project.vout,
    )
    context = normal_review_context.model_copy(
        update={
            "project": project,
            "calculated_inputs": {ReviewParameterName.IOUT: iout_result},
        }
    )

    finding = OutputPowerConsistencyRule().evaluate(context)

    assert finding.severity == Severity.PASS
    calculation_evidence_items = [
        evidence
        for evidence in finding.evidence
        if evidence.source == EvidenceSource.CALCULATION
    ]
    assert any(
        "LLC-IOUT-V1" in evidence.references
        for evidence in calculation_evidence_items
    )


@pytest.mark.parametrize("field", ["pout", "vout", "iout"])
def test_r010_requires_all_power_consistency_inputs(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
    field: str,
) -> None:
    context = update_review_context(normal_review_context, "project", **{field: None})

    assert OutputPowerConsistencyRule().evaluate(context).severity == Severity.INSUFFICIENT_DATA


def test_r010_requires_configured_tolerance(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    context = update_review_context(
        normal_review_context, "settings", output_power_relative_tolerance=None
    )

    finding = OutputPowerConsistencyRule().evaluate(context)

    assert finding.severity == Severity.INSUFFICIENT_DATA
    assert "settings.output_power_relative_tolerance" in finding.missing_information


def test_r010_rejects_invalid_power_units(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    context = update_review_context(normal_review_context, "project", iout=q(10, "V"))

    assert OutputPowerConsistencyRule().evaluate(context).severity == Severity.INSUFFICIENT_DATA
