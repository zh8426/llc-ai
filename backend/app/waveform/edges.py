from typing import Literal

import numpy as np
from numpy.typing import NDArray

from app.waveform.exceptions import WaveformAnalysisError, WaveformSchemaError
from app.waveform.models import EdgeDetectionResult
from app.waveform.preprocessing import require_strictly_increasing_time

AUTO_LOW_FRACTION = 0.3
AUTO_HIGH_FRACTION = 0.7
ROBUST_LOW_PERCENTILE = 5.0
ROBUST_HIGH_PERCENTILE = 95.0


def detect_rising_edges(
    time: NDArray[np.float64],
    signal: NDArray[np.float64],
    *,
    low_threshold: float | None = None,
    high_threshold: float | None = None,
) -> EdgeDetectionResult:
    return _detect_edges(
        time,
        signal,
        direction="rising",
        low_threshold=low_threshold,
        high_threshold=high_threshold,
    )


def detect_falling_edges(
    time: NDArray[np.float64],
    signal: NDArray[np.float64],
    *,
    low_threshold: float | None = None,
    high_threshold: float | None = None,
) -> EdgeDetectionResult:
    return _detect_edges(
        time,
        signal,
        direction="falling",
        low_threshold=low_threshold,
        high_threshold=high_threshold,
    )


def _detect_edges(
    time: NDArray[np.float64],
    signal: NDArray[np.float64],
    *,
    direction: Literal["rising", "falling"],
    low_threshold: float | None,
    high_threshold: float | None,
) -> EdgeDetectionResult:
    _validate_samples(time, signal)
    low, high, source = _resolve_thresholds(signal, low_threshold, high_threshold)
    indices: list[int] = []

    if direction == "rising":
        armed = bool(signal[0] <= low)
        for index, value in enumerate(signal[1:], start=1):
            if value <= low:
                armed = True
            elif armed and value >= high:
                indices.append(index)
                armed = False
    else:
        armed = bool(signal[0] >= high)
        for index, value in enumerate(signal[1:], start=1):
            if value >= high:
                armed = True
            elif armed and value <= low:
                indices.append(index)
                armed = False

    return EdgeDetectionResult(
        direction=direction,
        indices=tuple(indices),
        timestamps=tuple(float(time[index]) for index in indices),
        low_threshold=low,
        high_threshold=high,
        threshold_source=source,
    )


def _validate_samples(
    time: NDArray[np.float64], signal: NDArray[np.float64]
) -> None:
    if len(time) != len(signal):
        raise WaveformSchemaError("time and signal must contain the same number of samples")
    if len(signal) < 2:
        raise WaveformAnalysisError("edge detection requires at least two samples")
    if not np.all(np.isfinite(time)) or not np.all(np.isfinite(signal)):
        raise WaveformSchemaError("edge detection requires finite samples")
    require_strictly_increasing_time(time)


def _resolve_thresholds(
    signal: NDArray[np.float64],
    low_threshold: float | None,
    high_threshold: float | None,
) -> tuple[float, float, Literal["automatic", "explicit"]]:
    if (low_threshold is None) != (high_threshold is None):
        raise WaveformSchemaError("low_threshold and high_threshold must be provided together")
    if low_threshold is not None and high_threshold is not None:
        low = float(low_threshold)
        high = float(high_threshold)
        source: Literal["automatic", "explicit"] = "explicit"
    else:
        robust_low, robust_high = np.percentile(
            signal,
            [ROBUST_LOW_PERCENTILE, ROBUST_HIGH_PERCENTILE],
        )
        span = float(robust_high - robust_low)
        if not np.isfinite(span) or span <= 0.0:
            raise WaveformAnalysisError("signal has no usable amplitude span")
        low = float(robust_low + AUTO_LOW_FRACTION * span)
        high = float(robust_low + AUTO_HIGH_FRACTION * span)
        source = "automatic"
    if not np.isfinite(low) or not np.isfinite(high) or low >= high:
        raise WaveformSchemaError("edge thresholds must be finite and low < high")
    return low, high, source
