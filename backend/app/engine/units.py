from math import isfinite

from pint import UnitRegistry
from pint.errors import PintError

from app.engine.exceptions import InvalidEngineeringQuantityError
from app.schemas.engineering import EngineeringQuantity


_UNIT_REGISTRY = UnitRegistry()


def normalize_quantity(
    *,
    name: str,
    quantity: EngineeringQuantity,
    target_unit: str,
) -> EngineeringQuantity:
    """Validate dimensionality and return a finite converted quantity."""

    try:
        converted = _UNIT_REGISTRY.Quantity(quantity.value, quantity.unit).to(target_unit)
        normalized_value = float(converted.magnitude)
    except (PintError, TypeError, ValueError) as error:
        raise InvalidEngineeringQuantityError(
            f"{name} must use a unit compatible with {target_unit}; "
            f"received {quantity.unit!r}"
        ) from error

    if not isfinite(normalized_value):
        raise InvalidEngineeringQuantityError(f"{name} must convert to a finite value")

    return EngineeringQuantity(value=normalized_value, unit=target_unit)


def normalize_positive_quantity(
    *,
    name: str,
    quantity: EngineeringQuantity,
    target_unit: str,
) -> EngineeringQuantity:
    """Validate dimensionality and return a strictly positive quantity."""

    normalized = normalize_quantity(
        name=name,
        quantity=quantity,
        target_unit=target_unit,
    )
    if normalized.value <= 0.0:
        raise InvalidEngineeringQuantityError(f"{name} must be greater than zero")

    return normalized


def normalize_efficiency(quantity: EngineeringQuantity) -> EngineeringQuantity:
    """Normalize efficiency to a dimensionless ratio in the interval (0, 1]."""

    normalized = normalize_positive_quantity(
        name="efficiency",
        quantity=quantity,
        target_unit="dimensionless",
    )
    if normalized.value > 1.0:
        raise InvalidEngineeringQuantityError(
            "efficiency must be less than or equal to 1 when expressed as a ratio"
        )
    return normalized
