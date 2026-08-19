"""Deterministic FHA inductive/capacitive operating-region classification."""

from math import isclose
from typing import Final

from app.engine.exceptions import InvalidEngineeringQuantityError
from app.engine.gain import calculate_input_impedance
from app.schemas.engineering import (
    ComplexCalculationResult,
    EngineeringQuantity,
    OperatingRegionResult,
    OperatingRegionValue,
)

OPERATING_REGION_FORMULA_VERSION: Final = "LLC-REGION-FHA-V1"
# This is only a floating-point tie tolerance, not an engineering margin.
OPERATING_REGION_NUMERICAL_TOLERANCE_OHM: Final = 1e-12


def classify_operating_region(
    *, input_impedance: ComplexCalculationResult
) -> OperatingRegionResult:
    """Classify the region from the sign of ``Im(Zin)``.

    Positive imaginary input impedance is inductive, negative is capacitive,
    and values within the numerical tie tolerance are a boundary result.
    """

    if input_impedance.unit != "ohm":
        raise InvalidEngineeringQuantityError(
            "input_impedance must use the canonical ohm unit"
        )

    imaginary = input_impedance.imaginary
    if isclose(
        imaginary,
        0.0,
        rel_tol=0.0,
        abs_tol=OPERATING_REGION_NUMERICAL_TOLERANCE_OHM,
    ):
        operating_region: OperatingRegionValue = "BOUNDARY"
    elif imaginary > 0.0:
        operating_region = "INDUCTIVE"
    else:
        operating_region = "CAPACITIVE"

    return OperatingRegionResult(
        operating_region=operating_region,
        imaginary_impedance=EngineeringQuantity(value=imaginary, unit="ohm"),
        input_impedance=input_impedance,
        formula_version=OPERATING_REGION_FORMULA_VERSION,
    )


def calculate_operating_region(
    *,
    lr: EngineeringQuantity,
    lm: EngineeringQuantity,
    cr: EngineeringQuantity,
    equivalent_load: EngineeringQuantity,
    fs: EngineeringQuantity,
) -> OperatingRegionResult:
    """Calculate ``Zin`` and classify its FHA operating region."""

    input_impedance = calculate_input_impedance(
        lr=lr,
        lm=lm,
        cr=cr,
        equivalent_load=equivalent_load,
        fs=fs,
    )
    return classify_operating_region(input_impedance=input_impedance)
