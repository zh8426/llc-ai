import pytest

from app.engine import calculate_equivalent_load, calculate_fr, calculate_gain_curve
from app.engine.exceptions import InvalidEngineeringQuantityError
from app.schemas.engineering import EngineeringQuantity


def q(value: float, unit: str) -> EngineeringQuantity:
    return EngineeringQuantity(value=value, unit=unit)


def curve_inputs() -> dict[str, EngineeringQuantity]:
    equivalent_load = calculate_equivalent_load(
        pout=q(500, "W"), vout=q(48, "V"), transformer_ratio=q(4, "dimensionless")
    )
    return {
        "lr": q(45, "uH"),
        "lm": q(300, "uH"),
        "cr": q(47, "nF"),
        "equivalent_load": q(equivalent_load.value, equivalent_load.unit),
        "frequency_min": q(60, "kHz"),
        "frequency_max": q(180, "kHz"),
    }


def test_gain_curve_retains_traceable_points_and_regions() -> None:
    result = calculate_gain_curve(**curve_inputs(), point_count=11)

    assert result.formula_version == "LLC-GAIN-CURVE-FHA-V1"
    assert result.point_count == 11
    assert len(result.points) == 11
    assert result.frequency_min == q(60_000, "Hz")
    assert result.frequency_max == q(180_000, "Hz")
    assert result.points[0].switching_frequency == result.frequency_min
    assert result.points[-1].switching_frequency == result.frequency_max
    assert {point.operating_region for point in result.points} <= {
        "INDUCTIVE",
        "CAPACITIVE",
        "BOUNDARY",
    }
    assert all(
        point.tank_gain.formula_version == "LLC-GAIN-FHA-V1"
        for point in result.points
    )


def test_gain_curve_preserves_resonant_point_gain_invariant() -> None:
    inputs = curve_inputs()
    resonant_frequency = calculate_fr(lr=inputs["lr"], cr=inputs["cr"]).value
    inputs["frequency_min"] = q(resonant_frequency / 2, "Hz")
    inputs["frequency_max"] = q(resonant_frequency * 1.5, "Hz")
    result = calculate_gain_curve(**inputs, point_count=3)

    assert result.points[1].normalized_frequency.value == pytest.approx(1.0)
    assert result.points[1].tank_gain.value == pytest.approx(1.0, rel=1e-10)


@pytest.mark.parametrize(
    ("field", "value"),
    [("frequency_min", q(180, "kHz")), ("frequency_max", q(60, "kHz"))],
)
def test_gain_curve_rejects_non_increasing_frequency_range(
    field: str, value: EngineeringQuantity
) -> None:
    inputs = curve_inputs()
    inputs[field] = value

    with pytest.raises(InvalidEngineeringQuantityError):
        calculate_gain_curve(**inputs, point_count=11)


def test_gain_curve_rejects_unbounded_point_count() -> None:
    with pytest.raises(InvalidEngineeringQuantityError):
        calculate_gain_curve(**curve_inputs(), point_count=1002)
