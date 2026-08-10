from collections.abc import Callable

import pytest

from app.rules.builtin import (
    CriticalParameterCompletenessRule,
    InputVoltageOrderingRule,
    PositiveValuesRule,
    SwitchingFrequencyOrderingRule,
)
from app.schemas.engineering import EngineeringQuantity
from app.schemas.review import ReviewContext, Severity


def q(value: float, unit: str) -> EngineeringQuantity:
    return EngineeringQuantity(value=value, unit=unit)


def test_r001_passes_when_all_core_parameters_are_present(
    normal_review_context: ReviewContext,
) -> None:
    finding = CriticalParameterCompletenessRule().evaluate(normal_review_context)

    assert finding.severity == Severity.PASS
    assert finding.missing_information == ()


@pytest.mark.parametrize(
    "field",
    ["vin_min", "vin_nom", "vin_max", "vout", "pout", "lr", "lm", "cr", "fsw_min", "fsw_max"],
)
def test_r001_reports_each_missing_core_parameter(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
    field: str,
) -> None:
    context = update_review_context(normal_review_context, "project", **{field: None})

    finding = CriticalParameterCompletenessRule().evaluate(context)

    assert finding.severity == Severity.INSUFFICIENT_DATA
    assert field in finding.missing_information


def test_r002_passes_for_positive_dimensionally_valid_values(
    normal_review_context: ReviewContext,
) -> None:
    finding = PositiveValuesRule().evaluate(normal_review_context)

    assert finding.severity == Severity.PASS


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("vin_min", q(0, "V")),
        ("vout", q(-48, "V")),
        ("pout", q(0, "W")),
        ("lr", q(-45, "uH")),
        ("lm", q(0, "H")),
        ("cr", q(-47, "nF")),
        ("fsw_min", q(60, "V")),
    ],
)
def test_r002_marks_non_positive_or_wrong_dimension_as_critical(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
    field: str,
    invalid_value: EngineeringQuantity,
) -> None:
    context = update_review_context(
        normal_review_context, "project", **{field: invalid_value}
    )

    finding = PositiveValuesRule().evaluate(context)

    assert finding.severity == Severity.CRITICAL
    assert field in finding.missing_information
    assert finding.evidence


def test_r002_returns_insufficient_data_for_missing_value(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    context = update_review_context(normal_review_context, "project", cr=None)

    finding = PositiveValuesRule().evaluate(context)

    assert finding.severity == Severity.INSUFFICIENT_DATA
    assert "cr" in finding.missing_information


def test_r003_passes_for_ordered_input_voltage(
    normal_review_context: ReviewContext,
) -> None:
    assert InputVoltageOrderingRule().evaluate(normal_review_context).severity == Severity.PASS


@pytest.mark.parametrize(
    ("vin_min", "vin_nom", "vin_max"),
    [
        (q(360, "V"), q(300, "V"), q(420, "V")),
        (q(300, "V"), q(420, "V"), q(360, "V")),
    ],
)
def test_r003_marks_unordered_input_voltage_as_critical(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
    vin_min: EngineeringQuantity,
    vin_nom: EngineeringQuantity,
    vin_max: EngineeringQuantity,
) -> None:
    context = update_review_context(
        normal_review_context,
        "project",
        vin_min=vin_min,
        vin_nom=vin_nom,
        vin_max=vin_max,
    )

    finding = InputVoltageOrderingRule().evaluate(context)

    assert finding.severity == Severity.CRITICAL
    assert finding.evidence


def test_r003_accepts_equal_voltage_boundaries(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    context = update_review_context(
        normal_review_context,
        "project",
        vin_min=q(400, "V"),
        vin_nom=q(400, "V"),
        vin_max=q(400, "V"),
    )

    assert InputVoltageOrderingRule().evaluate(context).severity == Severity.PASS


def test_r003_handles_missing_and_invalid_voltage(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    missing = update_review_context(normal_review_context, "project", vin_nom=None)
    invalid = update_review_context(normal_review_context, "project", vin_min=q(300, "A"))

    assert InputVoltageOrderingRule().evaluate(missing).severity == Severity.INSUFFICIENT_DATA
    assert InputVoltageOrderingRule().evaluate(invalid).severity == Severity.CRITICAL


def test_r004_passes_for_strictly_ordered_switching_range(
    normal_review_context: ReviewContext,
) -> None:
    assert SwitchingFrequencyOrderingRule().evaluate(normal_review_context).severity == Severity.PASS


@pytest.mark.parametrize(
    ("fsw_min", "fsw_max"),
    [
        (q(150, "kHz"), q(60, "kHz")),
        (q(100, "kHz"), q(100, "kHz")),
    ],
)
def test_r004_marks_non_increasing_frequency_range_as_critical(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
    fsw_min: EngineeringQuantity,
    fsw_max: EngineeringQuantity,
) -> None:
    context = update_review_context(
        normal_review_context, "project", fsw_min=fsw_min, fsw_max=fsw_max
    )

    finding = SwitchingFrequencyOrderingRule().evaluate(context)

    assert finding.severity == Severity.CRITICAL
    assert finding.evidence


def test_r004_handles_missing_and_invalid_frequency(
    normal_review_context: ReviewContext,
    update_review_context: Callable[..., ReviewContext],
) -> None:
    missing = update_review_context(normal_review_context, "project", fsw_max=None)
    invalid = update_review_context(normal_review_context, "project", fsw_min=q(60, "V"))

    assert SwitchingFrequencyOrderingRule().evaluate(missing).severity == Severity.INSUFFICIENT_DATA
    assert SwitchingFrequencyOrderingRule().evaluate(invalid).severity == Severity.CRITICAL

