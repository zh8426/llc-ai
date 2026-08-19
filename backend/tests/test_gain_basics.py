from collections.abc import Callable
from math import pi

import pytest

from app.engine.exceptions import InvalidEngineeringQuantityError
from app.engine.gain import (
    EQUIVALENT_LOAD_FORMULA_VERSION,
    NORMALIZED_FREQUENCY_FORMULA_VERSION,
    OUTPUT_RESISTANCE_FORMULA_VERSION,
    QUALITY_FACTOR_FORMULA_VERSION,
    calculate_equivalent_load,
    calculate_normalized_frequency,
    calculate_output_resistance,
    calculate_quality_factor,
)
from app.schemas.engineering import CalculationResult, EngineeringQuantity


def quantity(value: float, unit: str) -> EngineeringQuantity:
    return EngineeringQuantity(value=value, unit=unit)


def test_calculate_output_resistance_matches_ro_definition() -> None:
    result = calculate_output_resistance(pout=quantity(500, "W"), vout=quantity(48, "V"))

    assert result.name == "output_resistance"
    assert result.value == pytest.approx(48**2 / 500)
    assert result.unit == "ohm"
    assert result.formula_version == OUTPUT_RESISTANCE_FORMULA_VERSION == "LLC-RO-FHA-V1"
    assert result.inputs["pout"] == quantity(500, "W")
    assert result.inputs["vout"] == quantity(48, "V")


def test_calculate_equivalent_load_matches_ti_fha_form() -> None:
    result = calculate_equivalent_load(
        pout=quantity(300, "W"),
        vout=quantity(12, "V"),
        transformer_ratio=quantity(16.5, "dimensionless"),
    )

    assert result.name == "equivalent_ac_load"
    assert result.value == pytest.approx(8 * 16.5**2 * 12**2 / (pi**2 * 300))
    assert result.unit == "ohm"
    assert result.formula_version == EQUIVALENT_LOAD_FORMULA_VERSION == "LLC-RE-FHA-V1"
    assert result.inputs["transformer_ratio"] == quantity(16.5, "dimensionless")


def test_calculate_quality_factor_uses_characteristic_impedance() -> None:
    result = calculate_quality_factor(
        lr=quantity(45, "uH"),
        cr=quantity(47, "nF"),
        equivalent_load=quantity(59.85, "ohm"),
    )

    assert result.name == "quality_factor"
    assert result.value == pytest.approx(30.942637387763806 / 59.85)
    assert result.unit == "dimensionless"
    assert result.formula_version == QUALITY_FACTOR_FORMULA_VERSION == "LLC-QE-FHA-V1"
    assert result.inputs["characteristic_impedance"].unit == "ohm"


def test_normalized_frequency_is_one_at_resonance() -> None:
    result = calculate_normalized_frequency(
        fs=quantity(100, "kHz"),
        fr=quantity(100_000, "Hz"),
    )

    assert result.name == "normalized_frequency"
    assert result.value == pytest.approx(1.0)
    assert result.unit == "dimensionless"
    assert result.formula_version == NORMALIZED_FREQUENCY_FORMULA_VERSION == "LLC-FN-FHA-V1"
    assert result.inputs["fs"] == quantity(100_000, "Hz")
    assert result.inputs["fr"] == quantity(100_000, "Hz")


def test_fha_basics_convert_equivalent_units() -> None:
    result = calculate_equivalent_load(
        pout=quantity(0.3, "kW"),
        vout=quantity(12_000, "mV"),
        transformer_ratio=quantity(16.5, "dimensionless"),
    )

    assert result.value == pytest.approx(8 * 16.5**2 * 12**2 / (pi**2 * 300))
    assert result.inputs["pout"] == quantity(300, "W")
    assert result.inputs["vout"] == quantity(12, "V")


@pytest.mark.parametrize(
    ("calculation", "arguments"),
    [
        (
            calculate_output_resistance,
            {"pout": quantity(0, "W"), "vout": quantity(48, "V")},
        ),
        (
            calculate_equivalent_load,
            {
                "pout": quantity(500, "W"),
                "vout": quantity(48, "V"),
                "transformer_ratio": quantity(0, "dimensionless"),
            },
        ),
        (
            calculate_quality_factor,
            {
                "lr": quantity(45, "uH"),
                "cr": quantity(47, "nF"),
                "equivalent_load": quantity(0, "ohm"),
            },
        ),
        (
            calculate_normalized_frequency,
            {"fs": quantity(0, "Hz"), "fr": quantity(100, "kHz")},
        ),
    ],
)
def test_each_fha_basic_rejects_non_positive_inputs(
    calculation: Callable[..., CalculationResult],
    arguments: dict[str, EngineeringQuantity],
) -> None:
    with pytest.raises(InvalidEngineeringQuantityError):
        calculation(**arguments)


def test_fha_basic_rejects_wrong_dimensions() -> None:
    with pytest.raises(InvalidEngineeringQuantityError):
        calculate_output_resistance(pout=quantity(500, "V"), vout=quantity(48, "V"))

    with pytest.raises(InvalidEngineeringQuantityError):
        calculate_equivalent_load(
            pout=quantity(500, "W"),
            vout=quantity(48, "V"),
            transformer_ratio=quantity(4, "V"),
        )
