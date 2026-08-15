from math import pi, sqrt
from typing import Final

from app.engine.results import build_calculation_result
from app.engine.units import normalize_positive_quantity
from app.schemas.engineering import CalculationResult, EngineeringQuantity

FR_FORMULA_VERSION: Final = "LLC-FR-V1"
FP_FORMULA_VERSION: Final = "LLC-FP-V1"
ZR_FORMULA_VERSION: Final = "LLC-ZR-V1"
LM_LR_RATIO_FORMULA_VERSION: Final = "LLC-LM-LR-RATIO-V1"


def calculate_fr(
    *, lr: EngineeringQuantity, cr: EngineeringQuantity
) -> CalculationResult:
    """Calculate fr = 1 / (2π√(LrCr)) using SI-normalized inputs."""

    normalized_lr = normalize_positive_quantity(name="lr", quantity=lr, target_unit="H")
    normalized_cr = normalize_positive_quantity(name="cr", quantity=cr, target_unit="F")

    value = 1.0 / (2.0 * pi * sqrt(normalized_lr.value) * sqrt(normalized_cr.value))

    return build_calculation_result(
        name="resonant_frequency",
        value=value,
        unit="Hz",
        inputs={"lr": normalized_lr, "cr": normalized_cr},
        formula_version=FR_FORMULA_VERSION,
    )


def calculate_fp(
    *,
    lr: EngineeringQuantity,
    lm: EngineeringQuantity,
    cr: EngineeringQuantity,
) -> CalculationResult:
    """Calculate fp = 1 / (2π√((Lr + Lm)Cr)) per project definition."""

    normalized_lr = normalize_positive_quantity(name="lr", quantity=lr, target_unit="H")
    normalized_lm = normalize_positive_quantity(name="lm", quantity=lm, target_unit="H")
    normalized_cr = normalize_positive_quantity(name="cr", quantity=cr, target_unit="F")
    total_inductance = normalized_lr.value + normalized_lm.value

    value = 1.0 / (2.0 * pi * sqrt(total_inductance) * sqrt(normalized_cr.value))

    return build_calculation_result(
        name="lower_resonant_frequency",
        value=value,
        unit="Hz",
        inputs={"lr": normalized_lr, "lm": normalized_lm, "cr": normalized_cr},
        formula_version=FP_FORMULA_VERSION,
    )


def calculate_zr(
    *, lr: EngineeringQuantity, cr: EngineeringQuantity
) -> CalculationResult:
    """Calculate Zr = √(Lr / Cr) using SI-normalized inputs."""

    normalized_lr = normalize_positive_quantity(name="lr", quantity=lr, target_unit="H")
    normalized_cr = normalize_positive_quantity(name="cr", quantity=cr, target_unit="F")

    value = sqrt(normalized_lr.value) / sqrt(normalized_cr.value)

    return build_calculation_result(
        name="characteristic_impedance",
        value=value,
        unit="ohm",
        inputs={"lr": normalized_lr, "cr": normalized_cr},
        formula_version=ZR_FORMULA_VERSION,
    )


def calculate_lm_lr_ratio(
    *, lr: EngineeringQuantity, lm: EngineeringQuantity
) -> CalculationResult:
    """Calculate the dimensionless inductance ratio Lm / Lr."""

    normalized_lr = normalize_positive_quantity(name="lr", quantity=lr, target_unit="H")
    normalized_lm = normalize_positive_quantity(name="lm", quantity=lm, target_unit="H")

    value = normalized_lm.value / normalized_lr.value

    return build_calculation_result(
        name="inductance_ratio",
        value=value,
        unit="dimensionless",
        inputs={"lm": normalized_lm, "lr": normalized_lr},
        formula_version=LM_LR_RATIO_FORMULA_VERSION,
    )
