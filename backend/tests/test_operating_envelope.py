import pytest

from app.engine import calculate_operating_envelope
from app.engine.gain import calculate_equivalent_load, calculate_gain_curve
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

    assert result.formula_version == "LLC-OPERATING-ENVELOPE-FHA-V2"
    assert result.available_gain_max is not None
    assert result.peak_point is not None
    assert result.available_gain_max.value == pytest.approx(
        result.peak_point.tank_gain.value
    )
    assert result.available_gain_frequency == result.peak_point.switching_frequency
    assert result.available_gain_max.formula_version == "LLC-AVAILABLE-GAIN-FHA-V2"
    assert result.peak_point.operating_region == "INDUCTIVE"
    assert result.required_gain_at_vin_min.value > result.required_gain_at_vin_nom.value
    assert result.required_gain_at_vin_nom.value > result.required_gain_at_vin_max.value
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


def test_operating_envelope_excludes_capacitive_peak_from_available_gain() -> None:
    inputs = sample_envelope_inputs()
    result = calculate_operating_envelope(**inputs)
    equivalent_load = calculate_equivalent_load(
        pout=inputs["pout"],
        vout=inputs["vout"],
        transformer_ratio=inputs["transformer_ratio"],
    )
    curve = calculate_gain_curve(
        lr=inputs["lr"],
        lm=inputs["lm"],
        cr=inputs["cr"],
        equivalent_load=quantity(equivalent_load.value, equivalent_load.unit),
        frequency_min=inputs["fsw_min"],
        frequency_max=inputs["fsw_max"],
        point_count=1001,
    )
    unrestricted_peak = max(curve.points, key=lambda point: point.tank_gain.value)

    assert unrestricted_peak.operating_region == "CAPACITIVE"
    assert result.available_gain_max is not None
    assert result.peak_point is not None
    assert result.peak_point.operating_region == "INDUCTIVE"
    assert result.available_gain_max.value < unrestricted_peak.tank_gain.value


def test_operating_envelope_reports_no_available_gain_without_inductive_points() -> None:
    inputs = sample_envelope_inputs()
    inputs["fsw_min"] = quantity(40, "kHz")
    inputs["fsw_max"] = quantity(60, "kHz")

    result = calculate_operating_envelope(**inputs)

    assert result.available_gain_max is None
    assert result.available_gain_frequency is None
    assert result.peak_point is None
