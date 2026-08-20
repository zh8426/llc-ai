"""Deterministic FHA operating-envelope calculations for Cross-Phase E1-F."""

from math import exp, log
from typing import Final

from app.engine.gain import (
    calculate_equivalent_load,
    calculate_fha_gain,
    calculate_input_impedance,
    calculate_normalized_frequency,
    calculate_quality_factor,
    calculate_required_gain,
)
from app.engine.operating_point import solve_operating_frequency
from app.engine.operating_region import classify_operating_region
from app.engine.resonant_tank import calculate_fr
from app.engine.results import build_calculation_result
from app.engine.units import normalize_positive_quantity, normalize_transformer_ratio
from app.schemas.engineering import (
    EngineeringQuantity,
    OperatingEnvelopePoint,
    OperatingEnvelopeResult,
)

OPERATING_ENVELOPE_FORMULA_VERSION: Final = "LLC-OPERATING-ENVELOPE-FHA-V2"
AVAILABLE_GAIN_FORMULA_VERSION: Final = "LLC-AVAILABLE-GAIN-FHA-V2"
ENVELOPE_SCAN_POINTS: Final = 2049


def _frequency_grid(frequency_min: float, frequency_max: float) -> tuple[float, ...]:
    if frequency_min == frequency_max:
        return (frequency_min,)
    log_min = log(frequency_min)
    step = (log(frequency_max) - log_min) / (ENVELOPE_SCAN_POINTS - 1)
    values = [exp(log_min + index * step) for index in range(ENVELOPE_SCAN_POINTS)]
    values[0] = frequency_min
    values[-1] = frequency_max
    return tuple(values)


def calculate_operating_envelope(
    *,
    lr: EngineeringQuantity,
    lm: EngineeringQuantity,
    cr: EngineeringQuantity,
    vin_min: EngineeringQuantity,
    vin_nom: EngineeringQuantity,
    vin_max: EngineeringQuantity,
    vout: EngineeringQuantity,
    pout: EngineeringQuantity,
    transformer_ratio: EngineeringQuantity,
    fsw_min: EngineeringQuantity,
    fsw_max: EngineeringQuantity,
) -> OperatingEnvelopeResult:
    """Calculate inductive-region FHA gain and operating points for Vin min/nom/max."""

    normalized_lr = normalize_positive_quantity(name="lr", quantity=lr, target_unit="H")
    normalized_lm = normalize_positive_quantity(name="lm", quantity=lm, target_unit="H")
    normalized_cr = normalize_positive_quantity(name="cr", quantity=cr, target_unit="F")
    normalized_vin_min = normalize_positive_quantity(
        name="vin_min", quantity=vin_min, target_unit="V"
    )
    normalized_vin_nom = normalize_positive_quantity(
        name="vin_nom", quantity=vin_nom, target_unit="V"
    )
    normalized_vin_max = normalize_positive_quantity(
        name="vin_max", quantity=vin_max, target_unit="V"
    )
    normalized_vout = normalize_positive_quantity(
        name="vout", quantity=vout, target_unit="V"
    )
    normalized_pout = normalize_positive_quantity(
        name="pout", quantity=pout, target_unit="W"
    )
    normalized_ratio = normalize_transformer_ratio(transformer_ratio)
    normalized_fsw_min = normalize_positive_quantity(
        name="fsw_min", quantity=fsw_min, target_unit="Hz"
    )
    normalized_fsw_max = normalize_positive_quantity(
        name="fsw_max", quantity=fsw_max, target_unit="Hz"
    )

    equivalent_load = calculate_equivalent_load(
        pout=normalized_pout,
        vout=normalized_vout,
        transformer_ratio=normalized_ratio,
    )
    equivalent_load_quantity = EngineeringQuantity(
        value=equivalent_load.value,
        unit=equivalent_load.unit,
    )
    resonant_frequency = calculate_fr(lr=normalized_lr, cr=normalized_cr)
    resonant_frequency_quantity = EngineeringQuantity(
        value=resonant_frequency.value,
        unit=resonant_frequency.unit,
    )
    quality_factor = calculate_quality_factor(
        lr=normalized_lr,
        cr=normalized_cr,
        equivalent_load=equivalent_load_quantity,
    )
    required_gain_at_vin_min = calculate_required_gain(
        vin=normalized_vin_min,
        vout=normalized_vout,
        transformer_ratio=normalized_ratio,
    )
    required_gain_at_vin_nom = calculate_required_gain(
        vin=normalized_vin_nom,
        vout=normalized_vout,
        transformer_ratio=normalized_ratio,
    )
    required_gain_at_vin_max = calculate_required_gain(
        vin=normalized_vin_max,
        vout=normalized_vout,
        transformer_ratio=normalized_ratio,
    )

    peak_point: OperatingEnvelopePoint | None = None
    for frequency in _frequency_grid(normalized_fsw_min.value, normalized_fsw_max.value):
        switching_frequency = EngineeringQuantity(value=frequency, unit="Hz")
        tank_gain = calculate_fha_gain(
            lr=normalized_lr,
            lm=normalized_lm,
            cr=normalized_cr,
            equivalent_load=equivalent_load_quantity,
            fs=switching_frequency,
        )
        input_impedance = calculate_input_impedance(
            lr=normalized_lr,
            lm=normalized_lm,
            cr=normalized_cr,
            equivalent_load=equivalent_load_quantity,
            fs=switching_frequency,
        )
        region = classify_operating_region(input_impedance=input_impedance)
        normalized_frequency = calculate_normalized_frequency(
            fs=switching_frequency,
            fr=resonant_frequency_quantity,
        )
        point = OperatingEnvelopePoint(
            switching_frequency=switching_frequency,
            normalized_frequency=normalized_frequency,
            tank_gain=tank_gain,
            operating_region=region.operating_region,
            input_impedance=input_impedance,
        )
        if point.operating_region == "INDUCTIVE" and (
            peak_point is None or point.tank_gain.value > peak_point.tank_gain.value
        ):
            peak_point = point

    available_gain_max = (
        None
        if peak_point is None
        else build_calculation_result(
            name="available_gain_max",
            value=peak_point.tank_gain.value,
            unit="dimensionless",
            inputs=peak_point.tank_gain.inputs,
            formula_version=AVAILABLE_GAIN_FORMULA_VERSION,
        )
    )
    operating_points = {
        "vin_min": solve_operating_frequency(
            lr=normalized_lr,
            lm=normalized_lm,
            cr=normalized_cr,
            vin=normalized_vin_min,
            vout=normalized_vout,
            pout=normalized_pout,
            transformer_ratio=normalized_ratio,
            fsw_min=normalized_fsw_min,
            fsw_max=normalized_fsw_max,
        ),
        "vin_nom": solve_operating_frequency(
            lr=normalized_lr,
            lm=normalized_lm,
            cr=normalized_cr,
            vin=normalized_vin_nom,
            vout=normalized_vout,
            pout=normalized_pout,
            transformer_ratio=normalized_ratio,
            fsw_min=normalized_fsw_min,
            fsw_max=normalized_fsw_max,
        ),
        "vin_max": solve_operating_frequency(
            lr=normalized_lr,
            lm=normalized_lm,
            cr=normalized_cr,
            vin=normalized_vin_max,
            vout=normalized_vout,
            pout=normalized_pout,
            transformer_ratio=normalized_ratio,
            fsw_min=normalized_fsw_min,
            fsw_max=normalized_fsw_max,
        ),
    }
    return OperatingEnvelopeResult(
        formula_version=OPERATING_ENVELOPE_FORMULA_VERSION,
        frequency_min=normalized_fsw_min,
        frequency_max=normalized_fsw_max,
        resonant_frequency=resonant_frequency,
        quality_factor=quality_factor,
        available_gain_max=available_gain_max,
        available_gain_frequency=(
            None if peak_point is None else peak_point.switching_frequency
        ),
        peak_point=peak_point,
        required_gain_at_vin_min=required_gain_at_vin_min,
        required_gain_at_vin_nom=required_gain_at_vin_nom,
        required_gain_at_vin_max=required_gain_at_vin_max,
        operating_points=operating_points,
    )
