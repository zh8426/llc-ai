from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from app.waveform.exceptions import WaveformAnalysisError, WaveformSchemaError
from app.waveform.models import (
    FrequencyMeasurement,
    ScalarWaveformFeature,
    SwitchingCycle,
)
from app.waveform.preprocessing import require_strictly_increasing_time


def calculate_switching_frequency(
    cycles: Sequence[SwitchingCycle],
) -> FrequencyMeasurement:
    if not cycles:
        raise WaveformAnalysisError("at least one complete switching cycle is required")
    durations = np.asarray([cycle.duration for cycle in cycles], dtype=np.float64)
    if not np.all(np.isfinite(durations)) or np.any(durations <= 0.0):
        raise WaveformSchemaError("cycle durations must be finite and greater than zero")
    mean_period = float(np.mean(durations))
    frequency = 1.0 / mean_period
    if not np.isfinite(frequency) or frequency <= 0.0:
        raise WaveformAnalysisError("switching frequency must be finite and positive")
    return FrequencyMeasurement(
        value=frequency,
        unit="Hz",
        cycle_count=len(cycles),
    )


def calculate_peak(
    signal: NDArray[np.float64], *, unit: str
) -> ScalarWaveformFeature:
    values = _require_finite_signal(signal, unit)
    return ScalarWaveformFeature(
        name="absolute_peak",
        value=float(np.max(np.abs(values))),
        unit=unit,
        sample_count=len(values),
        formula_version="WAVEFORM-ABS-PEAK-V1",
    )


def calculate_rms(
    signal: NDArray[np.float64],
    *,
    unit: str,
    time: NDArray[np.float64] | None = None,
) -> ScalarWaveformFeature:
    values = _require_finite_signal(signal, unit)
    if time is None:
        mean_square = float(np.mean(np.square(values)))
        formula_version = "WAVEFORM-RMS-SAMPLE-V1"
    else:
        if len(time) != len(values):
            raise WaveformSchemaError("time and signal must contain the same number of samples")
        if not np.all(np.isfinite(time)):
            raise WaveformSchemaError("RMS time samples must be finite")
        require_strictly_increasing_time(time)
        duration = float(time[-1] - time[0])
        mean_square = float(np.trapezoid(np.square(values), time) / duration)
        formula_version = "WAVEFORM-RMS-TIME-WEIGHTED-V1"
    value = float(np.sqrt(mean_square))
    if not np.isfinite(value):
        raise WaveformAnalysisError("RMS result must be finite")
    return ScalarWaveformFeature(
        name="rms",
        value=value,
        unit=unit,
        sample_count=len(values),
        formula_version=formula_version,
    )


def _require_finite_signal(
    signal: NDArray[np.float64], unit: str
) -> NDArray[np.float64]:
    if not unit.strip():
        raise WaveformSchemaError("feature unit must not be empty")
    if len(signal) == 0:
        raise WaveformAnalysisError("feature calculation requires samples")
    if not np.all(np.isfinite(signal)):
        raise WaveformSchemaError("feature calculation requires finite samples")
    return signal.astype(np.float64, copy=False)
