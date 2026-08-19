from math import hypot, isfinite

from app.engine.exceptions import CalculationRangeError
from app.schemas.engineering import (
    CalculationResult,
    ComplexCalculationResult,
    EngineeringQuantity,
)


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


def build_complex_calculation_result(
    *,
    name: str,
    real: float,
    imaginary: float,
    unit: str,
    inputs: dict[str, EngineeringQuantity],
    formula_version: str,
) -> ComplexCalculationResult:
    """Build a traceable complex result with a finite Euclidean magnitude."""

    magnitude = hypot(real, imaginary)
    if (
        not isfinite(real)
        or not isfinite(imaginary)
        or not isfinite(magnitude)
    ):
        raise CalculationRangeError(
            f"{name} could not produce a finite complex result from the supplied inputs"
        )

    return ComplexCalculationResult(
        name=name,
        real=real,
        imaginary=imaginary,
        magnitude=magnitude,
        unit=unit,
        inputs=inputs,
        formula_version=formula_version,
    )
