"""Deterministic LLC engineering calculations."""

from app.engine.gain import (
    calculate_equivalent_load,
    calculate_fha_gain,
    calculate_gain_curve,
    calculate_input_impedance,
    calculate_normalized_frequency,
    calculate_output_resistance,
    calculate_quality_factor,
    calculate_required_gain,
)
from app.engine.operating_envelope import calculate_operating_envelope
from app.engine.operating_point import solve_operating_frequency
from app.engine.operating_region import (
    calculate_operating_region,
    classify_operating_region,
)
from app.engine.power import calculate_input_power, calculate_output_current
from app.engine.resonant_tank import (
    calculate_fp,
    calculate_fr,
    calculate_lm_lr_ratio,
    calculate_zr,
)

__all__ = [
    "calculate_fp",
    "calculate_equivalent_load",
    "calculate_fha_gain",
    "calculate_gain_curve",
    "calculate_fr",
    "calculate_input_power",
    "calculate_input_impedance",
    "calculate_lm_lr_ratio",
    "calculate_normalized_frequency",
    "calculate_output_current",
    "calculate_output_resistance",
    "calculate_operating_region",
    "calculate_operating_envelope",
    "calculate_quality_factor",
    "calculate_required_gain",
    "classify_operating_region",
    "solve_operating_frequency",
    "calculate_zr",
]
