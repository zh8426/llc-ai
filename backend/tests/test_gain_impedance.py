from math import hypot, pi

import pytest

from app.engine.exceptions import InvalidEngineeringQuantityError
from app.engine.gain import (
    FHA_GAIN_FORMULA_VERSION,
    INPUT_IMPEDANCE_FORMULA_VERSION,
    calculate_fha_gain,
    calculate_input_impedance,
)
from app.engine.resonant_tank import calculate_fr
from app.schemas.engineering import ComplexCalculationResult, EngineeringQuantity


def quantity(value: float, unit: str) -> EngineeringQuantity:
    return EngineeringQuantity(value=value, unit=unit)


def sample_tank() -> dict[str, EngineeringQuantity]:
    return {
        "lr": quantity(45, "uH"),
        "lm": quantity(300, "uH"),
        "cr": quantity(47, "nF"),
        "equivalent_load": quantity(59.85, "ohm"),
        "fs": quantity(100, "kHz"),
    }


def test_input_impedance_returns_traceable_complex_result() -> None:
    result = calculate_input_impedance(**sample_tank())

    assert isinstance(result, ComplexCalculationResult)
    assert result.name == "input_impedance"
    assert result.unit == "ohm"
    assert result.formula_version == INPUT_IMPEDANCE_FORMULA_VERSION == "LLC-ZIN-FHA-V1"
    assert result.magnitude == pytest.approx(hypot(result.real, result.imaginary))
    assert result.inputs["lr"].value == pytest.approx(45e-6)
    assert result.inputs["cr"].value == pytest.approx(47e-9)
    assert result.inputs["fs"].value == pytest.approx(100_000)


def test_fha_gain_matches_complex_impedance_definition() -> None:
    parameters = sample_tank()
    gain = calculate_fha_gain(**parameters)
    lr = parameters["lr"].value * 1e-6
    lm = parameters["lm"].value * 1e-6
    cr = parameters["cr"].value * 1e-9
    load = parameters["equivalent_load"].value
    fs = parameters["fs"].value * 1e3
    omega = 2.0 * pi * fs
    z_lr = 1j * omega * lr
    z_cr = -1j / (omega * cr)
    z_lm = 1j * omega * lm
    z_parallel = (z_lm * load) / (z_lm + load)
    expected = abs(z_parallel / (z_lr + z_cr + z_parallel))

    assert gain.name == "fha_tank_gain"
    assert gain.unit == "dimensionless"
    assert gain.value == pytest.approx(expected)
    assert gain.formula_version == FHA_GAIN_FORMULA_VERSION == "LLC-GAIN-FHA-V1"


@pytest.mark.parametrize(
    ("lm", "equivalent_load"),
    [(quantity(150, "uH"), quantity(10, "ohm")), (quantity(600, "uH"), quantity(200, "ohm"))],
)
def test_fha_gain_is_unity_at_series_resonance(
    lm: EngineeringQuantity, equivalent_load: EngineeringQuantity
) -> None:
    parameters = sample_tank()
    parameters["lm"] = lm
    parameters["equivalent_load"] = equivalent_load
    fr = calculate_fr(lr=parameters["lr"], cr=parameters["cr"])
    parameters["fs"] = quantity(fr.value, fr.unit)

    gain = calculate_fha_gain(**parameters)

    assert gain.value == pytest.approx(1.0, rel=1e-10, abs=1e-10)


def test_fha_impedance_converts_equivalent_units() -> None:
    parameters = sample_tank()
    parameters["lr"] = quantity(0.000045, "H")
    parameters["lm"] = quantity(0.0003, "H")
    parameters["cr"] = quantity(0.000000047, "F")
    parameters["fs"] = quantity(100_000, "Hz")

    result = calculate_input_impedance(**parameters)

    assert result.inputs["lr"].value == pytest.approx(45e-6)
    assert result.inputs["lm"].value == pytest.approx(300e-6)
    assert result.inputs["cr"].value == pytest.approx(47e-9)


@pytest.mark.parametrize("field", ["lr", "lm", "cr", "equivalent_load", "fs"])
def test_fha_impedance_rejects_non_positive_input(field: str) -> None:
    parameters = sample_tank()
    parameters[field] = quantity(0, parameters[field].unit)

    with pytest.raises(InvalidEngineeringQuantityError):
        calculate_input_impedance(**parameters)
