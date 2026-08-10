from collections.abc import Callable

import pytest

from app.engine.exceptions import (
    CalculationRangeError,
    InvalidEngineeringQuantityError,
)
from app.engine.power import (
    INPUT_POWER_FORMULA_VERSION,
    OUTPUT_CURRENT_FORMULA_VERSION,
    calculate_input_power,
    calculate_output_current,
)
from app.schemas.engineering import CalculationResult, EngineeringQuantity


def quantity(value: float, unit: str) -> EngineeringQuantity:
    return EngineeringQuantity(value=value, unit=unit)


def test_calculate_output_current_matches_independent_reference() -> None:
    result = calculate_output_current(pout=quantity(500, "W"), vout=quantity(48, "V"))

    assert result.name == "output_current"
    assert result.value == pytest.approx(10.416666666666666, rel=1e-12)
    assert result.unit == "A"
    assert result.formula_version == OUTPUT_CURRENT_FORMULA_VERSION == "LLC-IOUT-V1"
    assert result.inputs == {
        "pout": quantity(500, "W"),
        "vout": quantity(48, "V"),
    }


def test_calculate_input_power_matches_independent_reference() -> None:
    result = calculate_input_power(
        pout=quantity(500, "W"), efficiency=quantity(0.94, "dimensionless")
    )

    assert result.name == "input_power"
    assert result.value == pytest.approx(531.9148936170213, rel=1e-12)
    assert result.unit == "W"
    assert result.formula_version == INPUT_POWER_FORMULA_VERSION == "LLC-PIN-V1"
    assert result.inputs == {
        "pout": quantity(500, "W"),
        "efficiency": quantity(0.94, "dimensionless"),
    }


def test_power_calculation_boundary_values_are_supported() -> None:
    current = calculate_output_current(pout=quantity(1, "W"), vout=quantity(1, "V"))
    input_power = calculate_input_power(
        pout=quantity(1, "W"), efficiency=quantity(1, "dimensionless")
    )

    assert current.value == 1.0
    assert input_power.value == 1.0


def test_power_calculations_convert_equivalent_units() -> None:
    current = calculate_output_current(pout=quantity(0.5, "kW"), vout=quantity(48, "V"))
    input_power = calculate_input_power(
        pout=quantity(0.5, "kW"), efficiency=quantity(94, "percent")
    )

    assert current.value == pytest.approx(10.416666666666666, rel=1e-12)
    assert current.inputs["pout"] == quantity(500, "W")
    assert input_power.value == pytest.approx(531.9148936170213, rel=1e-12)
    assert input_power.inputs["efficiency"].unit == "dimensionless"
    assert input_power.inputs["efficiency"].value == pytest.approx(0.94, rel=1e-15)


@pytest.mark.parametrize(
    ("calculation", "arguments"),
    [
        (
            calculate_output_current,
            {"pout": quantity(0, "W"), "vout": quantity(48, "V")},
        ),
        (
            calculate_input_power,
            {
                "pout": quantity(500, "W"),
                "efficiency": quantity(0, "dimensionless"),
            },
        ),
    ],
)
def test_each_power_calculation_rejects_non_positive_inputs(
    calculation: Callable[..., CalculationResult],
    arguments: dict[str, EngineeringQuantity],
) -> None:
    with pytest.raises(InvalidEngineeringQuantityError):
        calculation(**arguments)


@pytest.mark.parametrize(
    ("calculation", "arguments"),
    [
        (
            calculate_output_current,
            {"pout": quantity(500, "W"), "vout": quantity(48, "A")},
        ),
        (
            calculate_input_power,
            {"pout": quantity(500, "W"), "efficiency": quantity(94, "V")},
        ),
    ],
)
def test_each_power_calculation_rejects_wrong_dimensions(
    calculation: Callable[..., CalculationResult],
    arguments: dict[str, EngineeringQuantity],
) -> None:
    with pytest.raises(InvalidEngineeringQuantityError):
        calculation(**arguments)


def test_input_power_rejects_efficiency_above_unity() -> None:
    with pytest.raises(InvalidEngineeringQuantityError):
        calculate_input_power(
            pout=quantity(500, "W"), efficiency=quantity(1.01, "dimensionless")
        )


def test_engine_rejects_unknown_units_at_calculation_boundary() -> None:
    with pytest.raises(InvalidEngineeringQuantityError):
        calculate_output_current(
            pout=quantity(500, "not_a_unit"), vout=quantity(48, "V")
        )


@pytest.mark.parametrize(
    ("calculation", "incomplete_arguments"),
    [
        (calculate_output_current, {"pout": quantity(500, "W")}),
        (calculate_input_power, {"pout": quantity(500, "W")}),
    ],
)
def test_each_power_calculation_requires_all_declared_inputs(
    calculation: Callable[..., CalculationResult],
    incomplete_arguments: dict[str, EngineeringQuantity],
) -> None:
    with pytest.raises(TypeError):
        calculation(**incomplete_arguments)


def test_power_calculation_rejects_unrepresentable_result() -> None:
    with pytest.raises(CalculationRangeError):
        calculate_output_current(
            pout=quantity(1e308, "W"), vout=quantity(5e-324, "V")
        )
