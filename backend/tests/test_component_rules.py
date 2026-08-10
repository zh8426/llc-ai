from collections.abc import Callable

import pytest

from app.rules.builtin import (
    ControllerFrequencyCapabilityRule,
    MOSFETCurrentScreeningRule,
    MOSFETMeasuredPeakVoltageRule,
    MOSFETStaticVoltageScreeningRule,
    ResonantCapacitorRMSCurrentRule,
    ResonantCapacitorVoltageRatingRule,
)
from app.schemas.engineering import EngineeringQuantity
from app.schemas.review import ReviewContext, Severity


def q(value: float, unit: str) -> EngineeringQuantity:
    return EngineeringQuantity(value=value, unit=unit)


def test_r011_reports_only_static_screening_pass(
    normal_review_context: ReviewContext,
) -> None:
    finding = MOSFETStaticVoltageScreeningRule().evaluate(normal_review_context)

    assert finding.severity == Severity.PASS
    assert finding.description.startswith("Static screening passed.")
    assert "safety" in finding.description


@pytest.mark.parametrize("rating", [q(420, "V"), q(400, "V")])
def test_r011_is_critical_when_rating_is_not_above_vin_max(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
    rating: EngineeringQuantity,
) -> None:
    context = update_review_context(normal_review_context, "mosfet", vds_rating=rating)

    finding = MOSFETStaticVoltageScreeningRule().evaluate(context)

    assert finding.severity == Severity.CRITICAL
    assert finding.evidence
    assert finding.requires_engineer_confirmation is True


def test_r011_handles_missing_and_invalid_rating(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    missing = update_review_context(normal_review_context, "mosfet", vds_rating=None)
    invalid = update_review_context(normal_review_context, "mosfet", vds_rating=q(650, "A"))

    assert MOSFETStaticVoltageScreeningRule().evaluate(missing).severity == Severity.INSUFFICIENT_DATA
    assert MOSFETStaticVoltageScreeningRule().evaluate(invalid).severity == Severity.INSUFFICIENT_DATA


def test_r012_passes_configured_measured_vds_margin(
    normal_review_context: ReviewContext,
) -> None:
    finding = MOSFETMeasuredPeakVoltageRule().evaluate(normal_review_context)

    assert finding.severity == Severity.PASS
    assert finding.calculated_values["measured_vds_margin_ratio"].value == pytest.approx(
        150 / 650
    )


def test_r012_is_critical_above_absolute_rating(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    context = update_review_context(
        normal_review_context, "mosfet", measured_vds_peak=q(700, "V")
    )

    finding = MOSFETMeasuredPeakVoltageRule().evaluate(context)

    assert finding.severity == Severity.CRITICAL
    assert finding.evidence
    assert finding.requires_engineer_confirmation is True


def test_r012_warns_below_configured_margin(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    context = update_review_context(
        normal_review_context, "mosfet", measured_vds_peak=q(550, "V")
    )

    finding = MOSFETMeasuredPeakVoltageRule().evaluate(context)

    assert finding.severity == Severity.WARNING
    assert finding.evidence
    assert finding.requires_engineer_confirmation is True


def test_r012_without_margin_configuration_is_info_not_pass(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    context = update_review_context(
        normal_review_context, "settings", measured_vds_required_margin_ratio=None
    )

    finding = MOSFETMeasuredPeakVoltageRule().evaluate(context)

    assert finding.severity == Severity.INFO
    assert "settings.measured_vds_required_margin_ratio" in finding.missing_information


def test_r012_handles_missing_and_invalid_peak_data(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    missing = update_review_context(normal_review_context, "mosfet", measured_vds_peak=None)
    invalid = update_review_context(
        normal_review_context, "mosfet", measured_vds_peak=q(500, "A")
    )

    assert MOSFETMeasuredPeakVoltageRule().evaluate(missing).severity == Severity.INSUFFICIENT_DATA
    assert MOSFETMeasuredPeakVoltageRule().evaluate(invalid).severity == Severity.INSUFFICIENT_DATA


def test_r013_reports_below_rating_as_info_only(
    normal_review_context: ReviewContext,
) -> None:
    finding = MOSFETCurrentScreeningRule().evaluate(normal_review_context)

    assert finding.severity == Severity.INFO
    assert "not a complete current-safety conclusion" in finding.description


def test_r013_is_critical_when_measured_current_exceeds_rating(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    context = update_review_context(
        normal_review_context, "mosfet", measured_peak_current=q(25, "A")
    )

    finding = MOSFETCurrentScreeningRule().evaluate(context)

    assert finding.severity == Severity.CRITICAL
    assert finding.evidence


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("measured_peak_current", None),
        ("current_rating", None),
        ("current_temperature_condition", None),
    ],
)
def test_r013_requires_current_and_temperature_information(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
    field: str,
    value: object,
) -> None:
    context = update_review_context(normal_review_context, "mosfet", **{field: value})

    assert MOSFETCurrentScreeningRule().evaluate(context).severity == Severity.INSUFFICIENT_DATA


def test_r013_rejects_invalid_current_unit(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    context = update_review_context(
        normal_review_context, "mosfet", current_rating=q(20, "V")
    )

    assert MOSFETCurrentScreeningRule().evaluate(context).severity == Severity.INSUFFICIENT_DATA


def test_r014_reports_below_voltage_rating_as_info(
    normal_review_context: ReviewContext,
) -> None:
    finding = ResonantCapacitorVoltageRatingRule().evaluate(normal_review_context)

    assert finding.severity == Severity.INFO
    assert "no project voltage margin" in finding.description


def test_r014_is_critical_above_voltage_rating(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    context = update_review_context(
        normal_review_context, "resonant_capacitor", voltage_stress=q(1100, "V")
    )

    finding = ResonantCapacitorVoltageRatingRule().evaluate(context)

    assert finding.severity == Severity.CRITICAL
    assert finding.evidence


def test_r014_handles_missing_and_invalid_voltage_stress(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    missing = update_review_context(
        normal_review_context, "resonant_capacitor", voltage_stress=None
    )
    invalid = update_review_context(
        normal_review_context, "resonant_capacitor", voltage_stress=q(500, "A")
    )

    assert ResonantCapacitorVoltageRatingRule().evaluate(missing).severity == Severity.INSUFFICIENT_DATA
    assert ResonantCapacitorVoltageRatingRule().evaluate(invalid).severity == Severity.INSUFFICIENT_DATA


def test_r015_reports_below_rms_rating_as_info(
    normal_review_context: ReviewContext,
) -> None:
    finding = ResonantCapacitorRMSCurrentRule().evaluate(normal_review_context)

    assert finding.severity == Severity.INFO
    assert "not a thermal or lifetime conclusion" in finding.description


def test_r015_is_critical_above_rms_rating(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    context = update_review_context(
        normal_review_context, "resonant_capacitor", rms_current_stress=q(15, "A")
    )

    finding = ResonantCapacitorRMSCurrentRule().evaluate(context)

    assert finding.severity == Severity.CRITICAL
    assert finding.evidence


def test_r015_handles_missing_and_invalid_rms_stress(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    missing = update_review_context(
        normal_review_context, "resonant_capacitor", rms_current_rating=None
    )
    invalid = update_review_context(
        normal_review_context, "resonant_capacitor", rms_current_stress=q(8, "V")
    )

    assert ResonantCapacitorRMSCurrentRule().evaluate(missing).severity == Severity.INSUFFICIENT_DATA
    assert ResonantCapacitorRMSCurrentRule().evaluate(invalid).severity == Severity.INSUFFICIENT_DATA


def test_r016_passes_when_controller_covers_project_range(
    normal_review_context: ReviewContext,
) -> None:
    assert ControllerFrequencyCapabilityRule().evaluate(normal_review_context).severity == Severity.PASS


def test_r016_warns_when_controller_does_not_cover_project_range(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    context = update_review_context(
        normal_review_context, "controller", frequency_max=q(120, "kHz")
    )

    finding = ControllerFrequencyCapabilityRule().evaluate(context)

    assert finding.severity == Severity.WARNING
    assert finding.evidence


def test_r016_handles_missing_invalid_and_unordered_controller_range(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    missing = update_review_context(
        normal_review_context, "controller", frequency_min=None
    )
    invalid = update_review_context(
        normal_review_context, "controller", frequency_min=q(40, "V")
    )
    unordered = update_review_context(
        normal_review_context,
        "controller",
        frequency_min=q(500, "kHz"),
        frequency_max=q(40, "kHz"),
    )

    rule = ControllerFrequencyCapabilityRule()
    assert rule.evaluate(missing).severity == Severity.INSUFFICIENT_DATA
    assert rule.evaluate(invalid).severity == Severity.INSUFFICIENT_DATA
    assert rule.evaluate(unordered).severity == Severity.INSUFFICIENT_DATA

