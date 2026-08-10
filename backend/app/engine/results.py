from math import isfinite

from app.engine.exceptions import CalculationRangeError
from app.schemas.engineering import CalculationResult, EngineeringQuantity


def build_calculation_result(
    *,
    name: str,
    value: float,
    unit: str,
    inputs: dict[str, EngineeringQuantity],
    formula_version: str,
) -> CalculationResult:
    """Build a result only when the formula produced a finite positive scalar."""

    if not isfinite(value) or value <= 0.0:
        raise CalculationRangeError(
            f"{name} could not produce a finite positive result from the supplied inputs"
        )

    return CalculationResult(
        name=name,
        value=value,
        unit=unit,
        inputs=inputs,
        formula_version=formula_version,
    )

