"""Deterministic FHA quantities for Cross-Phase E1-B and E1-C."""

from math import pi
from typing import Final

from app.engine.exceptions import CalculationRangeError, InvalidEngineeringQuantityError
from app.engine.resonant_tank import calculate_fr, calculate_zr
from app.engine.results import (
    build_calculation_result,
    build_complex_calculation_result,
)
from app.engine.units import normalize_positive_quantity, normalize_transformer_ratio
from app.schemas.engineering import (
    CalculationResult,
    ComplexCalculationResult,
    EngineeringQuantity,
    GainCurvePoint,
    GainCurveResult,
)

OUTPUT_RESISTANCE_FORMULA_VERSION: Final = "LLC-RO-FHA-V1"
EQUIVALENT_LOAD_FORMULA_VERSION: Final = "LLC-RE-FHA-V1"
QUALITY_FACTOR_FORMULA_VERSION: Final = "LLC-QE-FHA-V1"
NORMALIZED_FREQUENCY_FORMULA_VERSION: Final = "LLC-FN-FHA-V1"
REQUIRED_GAIN_FORMULA_VERSION: Final = "LLC-MREQ-FHA-V2"
INPUT_IMPEDANCE_FORMULA_VERSION: Final = "LLC-ZIN-FHA-V1"
FHA_GAIN_FORMULA_VERSION: Final = "LLC-GAIN-FHA-V1"
GAIN_CURVE_FORMULA_VERSION: Final = "LLC-GAIN-CURVE-FHA-V1"
MAX_GAIN_CURVE_POINTS: Final = 1001


def _build_fha_network(
    *,
    lr: EngineeringQuantity,
    lm: EngineeringQuantity,
    cr: EngineeringQuantity,
    equivalent_load: EngineeringQuantity,
    fs: EngineeringQuantity,
) -> tuple[complex, complex, dict[str, EngineeringQuantity]]:
    """Return ``Zp``, ``Zin`` and the normalized FHA inputs."""

    normalized_lr = normalize_positive_quantity(name="lr", quantity=lr, target_unit="H")
    normalized_lm = normalize_positive_quantity(name="lm", quantity=lm, target_unit="H")
    normalized_cr = normalize_positive_quantity(name="cr", quantity=cr, target_unit="F")
    normalized_load = normalize_positive_quantity(
        name="equivalent_load", quantity=equivalent_load, target_unit="ohm"
    )
    normalized_fs = normalize_positive_quantity(name="fs", quantity=fs, target_unit="Hz")

    omega = 2.0 * pi * normalized_fs.value
    z_lr = complex(0.0, omega * normalized_lr.value)
    z_cr = complex(0.0, -1.0 / (omega * normalized_cr.value))
    z_lm = complex(0.0, omega * normalized_lm.value)
    z_parallel = (z_lm * normalized_load.value) / (z_lm + normalized_load.value)
    z_input = z_lr + z_cr + z_parallel

    return (
        z_parallel,
        z_input,
        {
            "lr": normalized_lr,
            "lm": normalized_lm,
            "cr": normalized_cr,
            "equivalent_load": normalized_load,
            "fs": normalized_fs,
        },
    )


def calculate_output_resistance(
    *, pout: EngineeringQuantity, vout: EngineeringQuantity
) -> CalculationResult:
    """Calculate the DC output load resistance Ro = Vout² / Pout."""

    normalized_pout = normalize_positive_quantity(
        name="pout", quantity=pout, target_unit="W"
    )
    normalized_vout = normalize_positive_quantity(
        name="vout", quantity=vout, target_unit="V"
    )
    value = normalized_vout.value**2 / normalized_pout.value
    return build_calculation_result(
        name="output_resistance",
        value=value,
        unit="ohm",
        inputs={"pout": normalized_pout, "vout": normalized_vout},
        formula_version=OUTPUT_RESISTANCE_FORMULA_VERSION,
    )


def calculate_equivalent_load(
    *,
    pout: EngineeringQuantity,
    vout: EngineeringQuantity,
    transformer_ratio: EngineeringQuantity,
) -> CalculationResult:
    """Calculate FHA equivalent primary load Re = 8 n² Ro / π²."""

    output_resistance = calculate_output_resistance(pout=pout, vout=vout)
    normalized_ratio = normalize_transformer_ratio(transformer_ratio)
    value = 8.0 * normalized_ratio.value**2 * output_resistance.value / pi**2
    return build_calculation_result(
        name="equivalent_ac_load",
        value=value,
        unit="ohm",
        inputs={
            "pout": output_resistance.inputs["pout"],
            "vout": output_resistance.inputs["vout"],
            "transformer_ratio": normalized_ratio,
            "output_resistance": EngineeringQuantity(
                value=output_resistance.value,
                unit=output_resistance.unit,
            ),
        },
        formula_version=EQUIVALENT_LOAD_FORMULA_VERSION,
    )


def calculate_quality_factor(
    *,
    lr: EngineeringQuantity,
    cr: EngineeringQuantity,
    equivalent_load: EngineeringQuantity,
) -> CalculationResult:
    """Calculate FHA quality factor Qe = Zr / Re."""

    normalized_load = normalize_positive_quantity(
        name="equivalent_load", quantity=equivalent_load, target_unit="ohm"
    )
    characteristic_impedance = calculate_zr(lr=lr, cr=cr)
    value = characteristic_impedance.value / normalized_load.value
    return build_calculation_result(
        name="quality_factor",
        value=value,
        unit="dimensionless",
        inputs={
            "lr": characteristic_impedance.inputs["lr"],
            "cr": characteristic_impedance.inputs["cr"],
            "equivalent_load": normalized_load,
            "characteristic_impedance": EngineeringQuantity(
                value=characteristic_impedance.value,
                unit=characteristic_impedance.unit,
            ),
        },
        formula_version=QUALITY_FACTOR_FORMULA_VERSION,
    )


def calculate_normalized_frequency(
    *, fs: EngineeringQuantity, fr: EngineeringQuantity
) -> CalculationResult:
    """Calculate normalized switching frequency Fn = fs / fr."""

    normalized_fs = normalize_positive_quantity(name="fs", quantity=fs, target_unit="Hz")
    normalized_fr = normalize_positive_quantity(name="fr", quantity=fr, target_unit="Hz")
    value = normalized_fs.value / normalized_fr.value
    return build_calculation_result(
        name="normalized_frequency",
        value=value,
        unit="dimensionless",
        inputs={"fs": normalized_fs, "fr": normalized_fr},
        formula_version=NORMALIZED_FREQUENCY_FORMULA_VERSION,
    )


def calculate_required_gain(
    *,
    vin: EngineeringQuantity,
    vout: EngineeringQuantity,
    transformer_ratio: EngineeringQuantity,
) -> CalculationResult:
    """Calculate half-bridge required gain ``Mreq = 2 n Vout / Vin``."""

    normalized_vin = normalize_positive_quantity(name="vin", quantity=vin, target_unit="V")
    normalized_vout = normalize_positive_quantity(
        name="vout", quantity=vout, target_unit="V"
    )
    normalized_ratio = normalize_transformer_ratio(transformer_ratio)
    value = (
        2.0 * normalized_ratio.value * normalized_vout.value / normalized_vin.value
    )
    return build_calculation_result(
        name="required_gain",
        value=value,
        unit="dimensionless",
        inputs={
            "vin": normalized_vin,
            "vout": normalized_vout,
            "transformer_ratio": normalized_ratio,
        },
        formula_version=REQUIRED_GAIN_FORMULA_VERSION,
    )


def calculate_input_impedance(
    *,
    lr: EngineeringQuantity,
    lm: EngineeringQuantity,
    cr: EngineeringQuantity,
    equivalent_load: EngineeringQuantity,
    fs: EngineeringQuantity,
) -> ComplexCalculationResult:
    """Calculate the FHA input impedance ``Zin = ZLr + ZCr + (ZLm || Re)``."""

    _, z_input, inputs = _build_fha_network(
        lr=lr,
        lm=lm,
        cr=cr,
        equivalent_load=equivalent_load,
        fs=fs,
    )
    return build_complex_calculation_result(
        name="input_impedance",
        real=z_input.real,
        imaginary=z_input.imag,
        unit="ohm",
        inputs=inputs,
        formula_version=INPUT_IMPEDANCE_FORMULA_VERSION,
    )


def calculate_fha_gain(
    *,
    lr: EngineeringQuantity,
    lm: EngineeringQuantity,
    cr: EngineeringQuantity,
    equivalent_load: EngineeringQuantity,
    fs: EngineeringQuantity,
) -> CalculationResult:
    """Calculate the FHA tank gain ``MFHA = |Zp / Zin|``."""

    z_parallel, z_input, inputs = _build_fha_network(
        lr=lr,
        lm=lm,
        cr=cr,
        equivalent_load=equivalent_load,
        fs=fs,
    )
    if z_input == 0j:
        raise CalculationRangeError("fha_tank_gain is undefined when input impedance is zero")

    return build_calculation_result(
        name="fha_tank_gain",
        value=abs(z_parallel / z_input),
        unit="dimensionless",
        inputs=inputs,
        formula_version=FHA_GAIN_FORMULA_VERSION,
    )


def calculate_gain_curve(
    *,
    lr: EngineeringQuantity,
    lm: EngineeringQuantity,
    cr: EngineeringQuantity,
    equivalent_load: EngineeringQuantity,
    frequency_min: EngineeringQuantity,
    frequency_max: EngineeringQuantity,
    point_count: int = 101,
) -> GainCurveResult:
    """Calculate a deterministic, linearly-spaced FHA gain curve.

    The sweep keeps every point's gain, normalized frequency, complex input
    impedance, and inductive/capacitive classification so callers can inspect
    the evidence instead of receiving an untraceable chart-only value.
    """

    from app.engine.operating_region import classify_operating_region
    if isinstance(point_count, bool) or not isinstance(point_count, int):
        raise InvalidEngineeringQuantityError("point_count must be an integer")
    if point_count < 2 or point_count > MAX_GAIN_CURVE_POINTS:
        raise InvalidEngineeringQuantityError(
            f"point_count must be between 2 and {MAX_GAIN_CURVE_POINTS}"
        )

    normalized_min = normalize_positive_quantity(
        name="frequency_min", quantity=frequency_min, target_unit="Hz"
    )
    normalized_max = normalize_positive_quantity(
        name="frequency_max", quantity=frequency_max, target_unit="Hz"
    )
    if normalized_max.value <= normalized_min.value:
        raise InvalidEngineeringQuantityError(
            "frequency_max must be greater than frequency_min"
        )

    resonant_frequency = calculate_fr(lr=lr, cr=cr)
    normalized_load = normalize_positive_quantity(
        name="equivalent_load", quantity=equivalent_load, target_unit="ohm"
    )
    quality_factor = calculate_quality_factor(
        lr=lr, cr=cr, equivalent_load=equivalent_load
    )
    points: list[GainCurvePoint] = []
    span = normalized_max.value - normalized_min.value
    for index in range(point_count):
        frequency = EngineeringQuantity(
            value=normalized_min.value + span * index / (point_count - 1),
            unit="Hz",
        )
        tank_gain = calculate_fha_gain(
            lr=lr,
            lm=lm,
            cr=cr,
            equivalent_load=equivalent_load,
            fs=frequency,
        )
        input_impedance = calculate_input_impedance(
            lr=lr,
            lm=lm,
            cr=cr,
            equivalent_load=equivalent_load,
            fs=frequency,
        )
        region = classify_operating_region(input_impedance=input_impedance)
        points.append(
            GainCurvePoint(
                switching_frequency=frequency,
                normalized_frequency=calculate_normalized_frequency(
                    fs=frequency,
                    fr=EngineeringQuantity(
                        value=resonant_frequency.value, unit=resonant_frequency.unit
                    ),
                ),
                tank_gain=tank_gain,
                input_impedance=input_impedance,
                operating_region=region.operating_region,
            )
        )

    return GainCurveResult(
        formula_version=GAIN_CURVE_FORMULA_VERSION,
        frequency_min=normalized_min,
        frequency_max=normalized_max,
        point_count=point_count,
        resonant_frequency=resonant_frequency,
        equivalent_load=build_calculation_result(
            name="equivalent_ac_load",
            value=normalized_load.value,
            unit="ohm",
            inputs={"equivalent_load": normalized_load},
            formula_version=EQUIVALENT_LOAD_FORMULA_VERSION,
        ),
        quality_factor=quality_factor,
        points=tuple(points),
    )
