import pytest

from app.engine.exceptions import InvalidEngineeringQuantityError
from app.engine.gain import (
    REQUIRED_GAIN_FORMULA_VERSION,
    calculate_required_gain,
)
from app.engine.operating_point import (
    OPERATING_POINT_FORMULA_VERSION,
    solve_operating_frequency,
)
from app.schemas.engineering import EngineeringQuantity


def quantity(value: float, unit: str) -> EngineeringQuantity:
    return EngineeringQuantity(value=value, unit=unit)


def sample_solver_inputs() -> dict[str, EngineeringQuantity]:
    return {
        "lr": quantity(45, "uH"),
        "lm": quantity(300, "uH"),
        "cr": quantity(47, "nF"),
        "vin": quantity(400, "V"),
        "vout": quantity(48, "V"),
        "pout": quantity(500, "W"),
        "transformer_ratio": quantity(4.17, "dimensionless"),
        "fsw_min": quantity(40, "kHz"),
        "fsw_max": quantity(180, "kHz"),
    }


def test_required_gain_matches_half_bridge_definition() -> None:
    result = calculate_required_gain(
        vin=quantity(400, "V"),
        vout=quantity(48, "V"),
        transformer_ratio=quantity(4.17, "dimensionless"),
    )

    assert result.name == "required_gain"
    assert result.value == pytest.approx(2 * 4.17 * 48 / 400)
    assert result.unit == "dimensionless"
    assert result.formula_version == REQUIRED_GAIN_FORMULA_VERSION == "LLC-MREQ-FHA-V2"
    assert result.inputs["vin"].unit == "V"
    assert result.inputs["transformer_ratio"].unit == "dimensionless"


def test_required_gain_normalizes_voltage_units() -> None:
    result = calculate_required_gain(
        vin=quantity(0.3, "kV"),
        vout=quantity(0.048, "kV"),
        transformer_ratio=quantity(4, "dimensionless"),
    )

    assert result.value == pytest.approx(1.28)
    assert result.inputs["vin"] == quantity(300, "V")
    assert result.inputs["vout"] == quantity(48, "V")


def test_required_gain_increases_when_input_voltage_decreases() -> None:
    low_line = calculate_required_gain(
        vin=quantity(300, "V"),
        vout=quantity(48, "V"),
        transformer_ratio=quantity(4, "dimensionless"),
    )
    high_line = calculate_required_gain(
        vin=quantity(420, "V"),
        vout=quantity(48, "V"),
        transformer_ratio=quantity(4, "dimensionless"),
    )

    assert low_line.value == pytest.approx(1.28)
    assert high_line.value == pytest.approx(32 / 35)
    assert low_line.value > high_line.value


def test_solver_retains_capacitive_and_inductive_roots_and_selects_inductive() -> None:
    result = solve_operating_frequency(**sample_solver_inputs())

    assert result.status == "VALID"
    assert result.model == "FHA"
    assert (
        result.formula_version
        == OPERATING_POINT_FORMULA_VERSION
        == "LLC-OPERATING-POINT-FHA-V2"
    )
    assert len(result.candidates) == 2
    assert [candidate.operating_region for candidate in result.candidates] == [
        "CAPACITIVE",
        "INDUCTIVE",
    ]
    assert result.candidates[0].eligible is False
    assert result.candidates[1].eligible is True
    assert result.operating_region == "INDUCTIVE"
    assert result.switching_frequency is not None
    assert 40_000 <= result.switching_frequency.value <= 180_000
    assert result.tank_gain is not None
    assert result.tank_gain.value == pytest.approx(result.required_gain.value, rel=1e-8)
    assert result.input_impedance is not None
    assert result.input_impedance.imaginary > 0.0


def test_solver_returns_evidence_when_only_capacitive_root_is_in_range() -> None:
    inputs = sample_solver_inputs()
    inputs["fsw_max"] = quantity(70, "kHz")

    result = solve_operating_frequency(**inputs)

    assert result.status == "NO_VALID_OPERATING_POINT"
    assert len(result.candidates) == 1
    assert result.candidates[0].operating_region == "CAPACITIVE"
    assert result.candidates[0].eligible is False
    assert result.switching_frequency is None
    assert result.input_impedance is None


def test_solver_rejects_reversed_frequency_range() -> None:
    inputs = sample_solver_inputs()
    inputs["fsw_min"] = quantity(180, "kHz")
    inputs["fsw_max"] = quantity(40, "kHz")

    with pytest.raises(InvalidEngineeringQuantityError):
        solve_operating_frequency(**inputs)


@pytest.mark.parametrize(
    "field",
    ["vin", "vout", "pout", "transformer_ratio", "fsw_min", "fsw_max"],
)
def test_solver_rejects_non_positive_required_inputs(field: str) -> None:
    inputs = sample_solver_inputs()
    inputs[field] = quantity(0, inputs[field].unit)

    with pytest.raises(InvalidEngineeringQuantityError):
        solve_operating_frequency(**inputs)
