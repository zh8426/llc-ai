from collections.abc import Callable

import pytest

from app.engine.exceptions import (
    CalculationRangeError,
    InvalidEngineeringQuantityError,
)
from app.engine.resonant_tank import (
    FP_FORMULA_VERSION,
    FR_FORMULA_VERSION,
    LM_LR_RATIO_FORMULA_VERSION,
    ZR_FORMULA_VERSION,
    calculate_fp,
    calculate_fr,
    calculate_lm_lr_ratio,
    calculate_zr,
)
from app.schemas.engineering import CalculationResult, EngineeringQuantity


def quantity(value: float, unit: str) -> EngineeringQuantity:
    return EngineeringQuantity(value=value, unit=unit)


def test_calculate_fr_matches_independent_reference_and_traces_si_inputs() -> None:
    result = calculate_fr(lr=quantity(45, "uH"), cr=quantity(47, "nF"))

    assert result.name == "resonant_frequency"
    assert result.value == pytest.approx(109_437.19316806001, rel=1e-12)
    assert result.unit == "Hz"
    assert result.formula_version == FR_FORMULA_VERSION == "LLC-FR-V1"
    assert result.inputs["lr"].unit == "H"
    assert result.inputs["lr"].value == pytest.approx(45e-6, rel=1e-15)
    assert result.inputs["cr"].unit == "F"
    assert result.inputs["cr"].value == pytest.approx(47e-9, rel=1e-15)


def test_calculate_fp_matches_independent_reference() -> None:
    result = calculate_fp(
        lr=quantity(45, "uH"),
        lm=quantity(300, "uH"),
        cr=quantity(47, "nF"),
    )

    assert result.name == "lower_resonant_frequency"
    assert result.value == pytest.approx(39_524.06957654706, rel=1e-12)
    assert result.unit == "Hz"
    assert result.formula_version == FP_FORMULA_VERSION == "LLC-FP-V1"


def test_calculate_zr_matches_independent_reference() -> None:
    result = calculate_zr(lr=quantity(45, "uH"), cr=quantity(47, "nF"))

    assert result.name == "characteristic_impedance"
    assert result.value == pytest.approx(30.942637387763806, rel=1e-12)
    assert result.unit == "ohm"
    assert result.formula_version == ZR_FORMULA_VERSION == "LLC-ZR-V1"


def test_calculate_lm_lr_ratio_matches_independent_reference() -> None:
    result = calculate_lm_lr_ratio(lr=quantity(45, "uH"), lm=quantity(300, "uH"))

    assert result.name == "inductance_ratio"
    assert result.value == pytest.approx(6.666666666666666, rel=1e-12)
    assert result.unit == "dimensionless"
    assert (
        result.formula_version
        == LM_LR_RATIO_FORMULA_VERSION
        == "LLC-LM-LR-RATIO-V1"
    )


def test_resonant_calculation_boundary_values_are_supported() -> None:
    assert calculate_fr(lr=quantity(1, "H"), cr=quantity(1, "F")).value == pytest.approx(
        0.15915494309189535
    )
    assert calculate_fp(
        lr=quantity(1, "H"), lm=quantity(1, "H"), cr=quantity(1, "F")
    ).value == pytest.approx(0.11253953951963826)
    assert calculate_zr(lr=quantity(1, "H"), cr=quantity(1, "F")).value == 1.0
    assert calculate_lm_lr_ratio(lr=quantity(1, "H"), lm=quantity(1, "H")).value == 1.0


def test_resonant_calculations_convert_equivalent_units() -> None:
    fr_si = calculate_fr(lr=quantity(45e-6, "H"), cr=quantity(47e-9, "F"))
    fr_scaled = calculate_fr(lr=quantity(45, "uH"), cr=quantity(47, "nF"))
    assert fr_scaled.value == pytest.approx(fr_si.value, rel=1e-15)

    fp_si = calculate_fp(
        lr=quantity(45e-6, "H"),
        lm=quantity(300e-6, "H"),
        cr=quantity(47e-9, "F"),
    )
    fp_scaled = calculate_fp(
        lr=quantity(0.045, "mH"),
        lm=quantity(0.3, "mH"),
        cr=quantity(0.047, "uF"),
    )
    assert fp_scaled.value == pytest.approx(fp_si.value, rel=1e-15)

    zr_scaled = calculate_zr(lr=quantity(0.045, "mH"), cr=quantity(0.047, "uF"))
    assert zr_scaled.value == pytest.approx(30.942637387763806, rel=1e-12)

    ratio_scaled = calculate_lm_lr_ratio(
        lr=quantity(0.045, "mH"), lm=quantity(300, "uH")
    )
    assert ratio_scaled.value == pytest.approx(6.666666666666666, rel=1e-12)


@pytest.mark.parametrize(
    ("calculation", "arguments"),
    [
        (calculate_fr, {"lr": quantity(0, "H"), "cr": quantity(47, "nF")}),
        (
            calculate_fp,
            {
                "lr": quantity(45, "uH"),
                "lm": quantity(-300, "uH"),
                "cr": quantity(47, "nF"),
            },
        ),
        (calculate_zr, {"lr": quantity(45, "uH"), "cr": quantity(0, "F")}),
        (
            calculate_lm_lr_ratio,
            {"lr": quantity(45, "uH"), "lm": quantity(0, "H")},
        ),
    ],
)
def test_each_resonant_calculation_rejects_non_positive_inputs(
    calculation: Callable[..., CalculationResult],
    arguments: dict[str, EngineeringQuantity],
) -> None:
    with pytest.raises(InvalidEngineeringQuantityError):
        calculation(**arguments)


@pytest.mark.parametrize(
    ("calculation", "arguments"),
    [
        (calculate_fr, {"lr": quantity(45, "V"), "cr": quantity(47, "nF")}),
        (
            calculate_fp,
            {
                "lr": quantity(45, "uH"),
                "lm": quantity(300, "W"),
                "cr": quantity(47, "nF"),
            },
        ),
        (calculate_zr, {"lr": quantity(45, "uH"), "cr": quantity(47, "H")}),
        (
            calculate_lm_lr_ratio,
            {"lr": quantity(45, "F"), "lm": quantity(300, "uH")},
        ),
    ],
)
def test_each_resonant_calculation_rejects_wrong_dimensions(
    calculation: Callable[..., CalculationResult],
    arguments: dict[str, EngineeringQuantity],
) -> None:
    with pytest.raises(InvalidEngineeringQuantityError):
        calculation(**arguments)


@pytest.mark.parametrize(
    ("calculation", "incomplete_arguments"),
    [
        (calculate_fr, {"lr": quantity(45, "uH")}),
        (
            calculate_fp,
            {"lr": quantity(45, "uH"), "lm": quantity(300, "uH")},
        ),
        (calculate_zr, {"cr": quantity(47, "nF")}),
        (calculate_lm_lr_ratio, {"lr": quantity(45, "uH")}),
    ],
)
def test_each_resonant_calculation_requires_all_declared_inputs(
    calculation: Callable[..., CalculationResult],
    incomplete_arguments: dict[str, EngineeringQuantity],
) -> None:
    with pytest.raises(TypeError):
        calculation(**incomplete_arguments)


def test_resonant_calculation_rejects_unrepresentable_result() -> None:
    with pytest.raises(CalculationRangeError):
        calculate_fr(lr=quantity(5e-324, "H"), cr=quantity(5e-324, "F"))


def test_unit_conversion_rejects_non_finite_si_value() -> None:
    with pytest.raises(InvalidEngineeringQuantityError):
        calculate_fr(lr=quantity(1e308, "YH"), cr=quantity(1, "F"))
