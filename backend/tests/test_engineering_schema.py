import math

import pytest
from pydantic import ValidationError

from app.schemas.engineering import EngineeringQuantity


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_engineering_quantity_rejects_non_finite_values(value: float) -> None:
    with pytest.raises(ValidationError):
        EngineeringQuantity(value=value, unit="V")


@pytest.mark.parametrize("value", [True, "45"])
def test_engineering_quantity_rejects_non_numeric_json_values(value: object) -> None:
    with pytest.raises(ValidationError):
        EngineeringQuantity(value=value, unit="uH")


@pytest.mark.parametrize("unit", ["", "   "])
def test_engineering_quantity_rejects_empty_units(unit: str) -> None:
    with pytest.raises(ValidationError):
        EngineeringQuantity(value=45, unit=unit)


def test_engineering_quantity_strips_unit_whitespace() -> None:
    result = EngineeringQuantity(value=45, unit="  uH  ")

    assert result.unit == "uH"

