"""Deterministic FHA required-gain and operating-frequency solver."""

from collections.abc import Callable
from math import exp, isclose, log
from typing import Final

from app.engine.exceptions import InvalidEngineeringQuantityError
from app.engine.gain import (
    calculate_equivalent_load,
    calculate_fha_gain,
    calculate_input_impedance,
    calculate_normalized_frequency,
    calculate_quality_factor,
    calculate_required_gain,
)
from app.engine.operating_region import classify_operating_region
from app.engine.resonant_tank import calculate_fr
from app.engine.units import normalize_positive_quantity, normalize_transformer_ratio
from app.schemas.engineering import (
    EngineeringQuantity,
    OperatingPointCandidate,
    OperatingPointResult,
)

OPERATING_POINT_FORMULA_VERSION: Final = "LLC-OPERATING-POINT-FHA-V1"
SOLVER_SCAN_POINTS: Final = 2049
SOLVER_BISECTION_ITERATIONS: Final = 80
# Numerical tolerances below are solver convergence settings, not engineering margins.
SOLVER_GAIN_RESIDUAL_TOLERANCE: Final = 1e-10
SOLVER_FREQUENCY_RELATIVE_TOLERANCE: Final = 1e-10


def _frequency_grid(frequency_min: float, frequency_max: float) -> tuple[float, ...]:
    """Build a deterministic logarithmic frequency grid including both endpoints."""

    if frequency_min == frequency_max:
        return (frequency_min,)

    log_min = log(frequency_min)
    log_max = log(frequency_max)
    step = (log_max - log_min) / (SOLVER_SCAN_POINTS - 1)
    values = [exp(log_min + index * step) for index in range(SOLVER_SCAN_POINTS)]
    values[0] = frequency_min
    values[-1] = frequency_max
    return tuple(values)


def _bisect_root(
    *,
    evaluate: Callable[[float], float],
    left: float,
    right: float,
    left_value: float,
) -> float:
    """Refine one sign-changing gain residual bracket with bisection."""

    for _ in range(SOLVER_BISECTION_ITERATIONS):
        middle = (left + right) / 2.0
        middle_value = evaluate(middle)
        if abs(middle_value) <= SOLVER_GAIN_RESIDUAL_TOLERANCE:
            return middle
        if isclose(
            left,
            right,
            rel_tol=SOLVER_FREQUENCY_RELATIVE_TOLERANCE,
            abs_tol=0.0,
        ):
            return middle
        if left_value * middle_value <= 0.0:
            right = middle
        else:
            left = middle
            left_value = middle_value

    return (left + right) / 2.0


def _append_unique_root(roots: list[float], root: float) -> None:
    """Retain one representative for numerically repeated roots."""

    if any(
        isclose(
            root,
            existing,
            rel_tol=SOLVER_FREQUENCY_RELATIVE_TOLERANCE,
            abs_tol=0.0,
        )
        for existing in roots
    ):
        return
    roots.append(root)


def _find_roots(
    *,
    evaluate: Callable[[float], float],
    frequency_min: float,
    frequency_max: float,
) -> tuple[float, ...]:
    """Find all sign-changing roots in the configured positive frequency range."""

    frequencies = _frequency_grid(frequency_min, frequency_max)
    roots: list[float] = []
    previous_frequency = frequencies[0]
    previous_value = evaluate(previous_frequency)
    if abs(previous_value) <= SOLVER_GAIN_RESIDUAL_TOLERANCE:
        _append_unique_root(roots, previous_frequency)

    for frequency in frequencies[1:]:
        value = evaluate(frequency)
        if abs(value) <= SOLVER_GAIN_RESIDUAL_TOLERANCE:
            _append_unique_root(roots, frequency)
        elif previous_value * value < 0.0:
            root = _bisect_root(
                evaluate=evaluate,
                left=previous_frequency,
                right=frequency,
                left_value=previous_value,
            )
            _append_unique_root(roots, root)
        previous_frequency = frequency
        previous_value = value

    roots.sort()
    return tuple(roots)


def _build_candidate(
    *,
    switching_frequency: EngineeringQuantity,
    fr: EngineeringQuantity,
    equivalent_load: EngineeringQuantity,
    lr: EngineeringQuantity,
    lm: EngineeringQuantity,
    cr: EngineeringQuantity,
) -> OperatingPointCandidate:
    tank_gain = calculate_fha_gain(
        lr=lr,
        lm=lm,
        cr=cr,
        equivalent_load=equivalent_load,
        fs=switching_frequency,
    )
    input_impedance = calculate_input_impedance(
        lr=lr,
        lm=lm,
        cr=cr,
        equivalent_load=equivalent_load,
        fs=switching_frequency,
    )
    region = classify_operating_region(input_impedance=input_impedance)
    normalized_frequency = calculate_normalized_frequency(
        fs=switching_frequency,
        fr=fr,
    )
    eligible = region.operating_region == "INDUCTIVE"
    rejection_reasons = () if eligible else ("operating_region_not_inductive",)
    return OperatingPointCandidate(
        switching_frequency=switching_frequency,
        normalized_frequency=normalized_frequency,
        tank_gain=tank_gain,
        operating_region=region.operating_region,
        input_impedance=input_impedance,
        eligible=eligible,
        rejection_reasons=rejection_reasons,
    )


def solve_operating_frequency(
    *,
    lr: EngineeringQuantity,
    lm: EngineeringQuantity,
    cr: EngineeringQuantity,
    vin: EngineeringQuantity,
    vout: EngineeringQuantity,
    pout: EngineeringQuantity,
    transformer_ratio: EngineeringQuantity,
    fsw_min: EngineeringQuantity,
    fsw_max: EngineeringQuantity,
) -> OperatingPointResult:
    """Solve ``MFHA(fsw) = Mreq`` and select only an inductive root."""

    normalized_lr = normalize_positive_quantity(name="lr", quantity=lr, target_unit="H")
    normalized_lm = normalize_positive_quantity(name="lm", quantity=lm, target_unit="H")
    normalized_cr = normalize_positive_quantity(name="cr", quantity=cr, target_unit="F")
    normalized_vin = normalize_positive_quantity(name="vin", quantity=vin, target_unit="V")
    normalized_vout = normalize_positive_quantity(
        name="vout", quantity=vout, target_unit="V"
    )
    normalized_pout = normalize_positive_quantity(name="pout", quantity=pout, target_unit="W")
    normalized_ratio = normalize_transformer_ratio(transformer_ratio)
    normalized_fsw_min = normalize_positive_quantity(
        name="fsw_min", quantity=fsw_min, target_unit="Hz"
    )
    normalized_fsw_max = normalize_positive_quantity(
        name="fsw_max", quantity=fsw_max, target_unit="Hz"
    )
    if normalized_fsw_min.value > normalized_fsw_max.value:
        raise InvalidEngineeringQuantityError("fsw_min must not be greater than fsw_max")

    required_gain = calculate_required_gain(
        vin=normalized_vin,
        vout=normalized_vout,
        transformer_ratio=normalized_ratio,
    )
    equivalent_load = calculate_equivalent_load(
        pout=normalized_pout,
        vout=normalized_vout,
        transformer_ratio=normalized_ratio,
    )
    quality_factor = calculate_quality_factor(
        lr=normalized_lr,
        cr=normalized_cr,
        equivalent_load=EngineeringQuantity(
            value=equivalent_load.value,
            unit=equivalent_load.unit,
        ),
    )
    resonant_frequency = calculate_fr(lr=normalized_lr, cr=normalized_cr)
    fr = EngineeringQuantity(value=resonant_frequency.value, unit=resonant_frequency.unit)

    def evaluate(frequency: float) -> float:
        gain = calculate_fha_gain(
            lr=normalized_lr,
            lm=normalized_lm,
            cr=normalized_cr,
            equivalent_load=EngineeringQuantity(
                value=equivalent_load.value,
                unit=equivalent_load.unit,
            ),
            fs=EngineeringQuantity(value=frequency, unit="Hz"),
        )
        return gain.value - required_gain.value

    roots = _find_roots(
        evaluate=evaluate,
        frequency_min=normalized_fsw_min.value,
        frequency_max=normalized_fsw_max.value,
    )
    candidates = tuple(
        _build_candidate(
            switching_frequency=EngineeringQuantity(value=root, unit="Hz"),
            fr=fr,
            equivalent_load=EngineeringQuantity(
                value=equivalent_load.value,
                unit=equivalent_load.unit,
            ),
            lr=normalized_lr,
            lm=normalized_lm,
            cr=normalized_cr,
        )
        for root in roots
    )
    selected = next((candidate for candidate in candidates if candidate.eligible), None)

    return OperatingPointResult(
        status="VALID" if selected is not None else "NO_VALID_OPERATING_POINT",
        model="FHA",
        formula_version=OPERATING_POINT_FORMULA_VERSION,
        vin=normalized_vin,
        load_power=normalized_pout,
        equivalent_load=equivalent_load,
        required_gain=required_gain,
        quality_factor=quality_factor,
        candidates=candidates,
        switching_frequency=None if selected is None else selected.switching_frequency,
        normalized_frequency=None if selected is None else selected.normalized_frequency,
        tank_gain=None if selected is None else selected.tank_gain,
        operating_region=None if selected is None else selected.operating_region,
        input_impedance=None if selected is None else selected.input_impedance,
    )
