import pytest

from app.engine import calculate_operating_envelope
from app.schemas.engineering import EngineeringQuantity


def quantity(value: float, unit: str) -> EngineeringQuantity:
    return EngineeringQuantity(value=value, unit=unit)


def sample_envelope_inputs() -> dict[str, EngineeringQuantity]:
    return {
        "lr": quantity(45, "uH"),
        "lm": quantity(300, "uH"),
        "cr": quantity(47, "nF"),
        "vin_min": quantity(300, "V"),
        "vin_nom": quantity(360, "V"),
        "vin_max": quantity(420, "V"),
        "vout": quantity(48, "V"),
        "pout": quantity(500, "W"),
        "transformer_ratio": quantity(4, "dimensionless"),
        "fsw_min": quantity(60, "kHz"),
        "fsw_max": quantity(150, "kHz"),
    }


def test_operating_envelope_calculates_required_gains_and_peak() -> None:
    result = calculate_operating_envelope(**sample_envelope_inputs())

    assert result.formula_version == "LLC-OPERATING-ENVELOPE-FHA-V1"
    assert result.available_gain_max.value == pytest.approx(
        result.peak_point.tank_gain.value
    )
    assert result.available_gain_frequency == result.peak_point.switching_frequency
    assert result.required_gain_at_vin_min.value < result.required_gain_at_vin_nom.value
    assert result.required_gain_at_vin_nom.value < result.required_gain_at_vin_max.value
    assert set(result.operating_points) == {"vin_min", "vin_nom", "vin_max"}
    assert result.operating_points["vin_nom"].status == "VALID"


def test_operating_envelope_normalizes_units() -> None:
    inputs = sample_envelope_inputs()
    inputs["vin_min"] = quantity(0.3, "kV")
    inputs["fsw_min"] = quantity(60_000, "Hz")
    inputs["fsw_max"] = quantity(150_000, "Hz")

    result = calculate_operating_envelope(**inputs)

    assert result.frequency_min == quantity(60_000, "Hz")
    assert result.frequency_max == quantity(150_000, "Hz")
    assert result.required_gain_at_vin_min.inputs["vin"].value == pytest.approx(300)
