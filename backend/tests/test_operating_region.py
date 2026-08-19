import pytest

from app.engine.exceptions import InvalidEngineeringQuantityError
from app.engine.gain import calculate_input_impedance
from app.engine.operating_region import (
    OPERATING_REGION_FORMULA_VERSION,
    calculate_operating_region,
    classify_operating_region,
)
from app.schemas.engineering import ComplexCalculationResult, EngineeringQuantity


def quantity(value: float, unit: str) -> EngineeringQuantity:
    return EngineeringQuantity(value=value, unit=unit)


def sample_tank() -> dict[str, EngineeringQuantity]:
    return {
        "lr": quantity(45, "uH"),
        "lm": quantity(300, "uH"),
        "cr": quantity(47, "nF"),
        "equivalent_load": quantity(59.85, "ohm"),
    }


@pytest.mark.parametrize(
    ("frequency", "expected_region"),
    [(40, "CAPACITIVE"), (100, "INDUCTIVE")],
)
def test_operating_region_uses_input_impedance_sign(
    frequency: float, expected_region: str
) -> None:
    result = calculate_operating_region(
        **sample_tank(), fs=quantity(frequency, "kHz")
    )

    assert result.operating_region == expected_region
    assert result.formula_version == OPERATING_REGION_FORMULA_VERSION == "LLC-REGION-FHA-V1"
    assert result.imaginary_impedance.unit == "ohm"
    assert result.imaginary_impedance.value == pytest.approx(
        result.input_impedance.imaginary
    )


@pytest.mark.parametrize("imaginary", [0.0, 1e-13, -1e-13])
def test_operating_region_near_zero_is_boundary(imaginary: float) -> None:
    input_impedance = ComplexCalculationResult(
        name="input_impedance",
        real=10.0,
        imaginary=imaginary,
        magnitude=10.0,
        unit="ohm",
        inputs={},
        formula_version="LLC-ZIN-FHA-V1",
    )

    result = classify_operating_region(input_impedance=input_impedance)

    assert result.operating_region == "BOUNDARY"


def test_classification_preserves_input_impedance_evidence() -> None:
    input_impedance = calculate_input_impedance(
        **sample_tank(), fs=quantity(100, "kHz")
    )

    result = classify_operating_region(input_impedance=input_impedance)

    assert result.input_impedance == input_impedance


def test_classification_rejects_non_ohm_impedance() -> None:
    input_impedance = ComplexCalculationResult(
        name="input_impedance",
        real=1.0,
        imaginary=1.0,
        magnitude=2**0.5,
        unit="V",
        inputs={},
        formula_version="LLC-ZIN-FHA-V1",
    )

    with pytest.raises(InvalidEngineeringQuantityError):
        classify_operating_region(input_impedance=input_impedance)
