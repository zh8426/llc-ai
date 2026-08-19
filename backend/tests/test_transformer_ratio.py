import pytest

from app.engine.exceptions import InvalidEngineeringQuantityError
from app.engine.units import normalize_transformer_ratio
from app.schemas.engineering import EngineeringQuantity


def quantity(value: float, unit: str) -> EngineeringQuantity:
    return EngineeringQuantity(value=value, unit=unit)


def test_transformer_ratio_uses_primary_to_secondary_convention() -> None:
    result = normalize_transformer_ratio(quantity(10, "dimensionless"))

    assert result.value == 10.0
    assert result.unit == "dimensionless"


@pytest.mark.parametrize("value", [0.0, -1.0])
def test_transformer_ratio_requires_a_positive_turns_ratio(value: float) -> None:
    with pytest.raises(InvalidEngineeringQuantityError):
        normalize_transformer_ratio(quantity(value, "dimensionless"))


def test_transformer_ratio_rejects_physical_units() -> None:
    with pytest.raises(InvalidEngineeringQuantityError):
        normalize_transformer_ratio(quantity(4, "V"))

