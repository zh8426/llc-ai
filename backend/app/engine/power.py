from typing import Final

from app.engine.results import build_calculation_result
from app.engine.units import normalize_efficiency, normalize_positive_quantity
from app.schemas.engineering import CalculationResult, EngineeringQuantity


OUTPUT_CURRENT_FORMULA_VERSION: Final = "LLC-IOUT-V1"
INPUT_POWER_FORMULA_VERSION: Final = "LLC-PIN-V1"


def calculate_output_current(
    *, pout: EngineeringQuantity, vout: EngineeringQuantity
) -> CalculationResult:
    """Calculate Iout = Pout / Vout using values from the same operating point."""

    normalized_pout = normalize_positive_quantity(
        name="pout", quantity=pout, target_unit="W"
    )
    normalized_vout = normalize_positive_quantity(
        name="vout", quantity=vout, target_unit="V"
    )

    value = normalized_pout.value / normalized_vout.value

    return build_calculation_result(
        name="output_current",
        value=value,
        unit="A",
        inputs={"pout": normalized_pout, "vout": normalized_vout},
        formula_version=OUTPUT_CURRENT_FORMULA_VERSION,
    )


def calculate_input_power(
    *, pout: EngineeringQuantity, efficiency: EngineeringQuantity
) -> CalculationResult:
    """Estimate Pin = Pout / efficiency using a supplied efficiency ratio."""

    normalized_pout = normalize_positive_quantity(
        name="pout", quantity=pout, target_unit="W"
    )
    normalized_efficiency = normalize_efficiency(efficiency)

    value = normalized_pout.value / normalized_efficiency.value

    return build_calculation_result(
        name="input_power",
        value=value,
        unit="W",
        inputs={"pout": normalized_pout, "efficiency": normalized_efficiency},
        formula_version=INPUT_POWER_FORMULA_VERSION,
    )
