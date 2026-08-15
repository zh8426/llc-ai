import numpy as np
from numpy.typing import NDArray

from app.waveform.exceptions import WaveformAnalysisError, WaveformSchemaError
from app.waveform.models import EdgeDetectionResult, SwitchingCycle
from app.waveform.preprocessing import require_strictly_increasing_time


def segment_cycles(
    time: NDArray[np.float64], rising_edges: EdgeDetectionResult
) -> tuple[SwitchingCycle, ...]:
    """Create complete switching cycles between adjacent rising edges."""

    require_strictly_increasing_time(time)
    if rising_edges.direction != "rising":
        raise WaveformSchemaError("cycle segmentation requires rising edges")
    if len(rising_edges.indices) != len(rising_edges.timestamps):
        raise WaveformSchemaError("edge indices and timestamps must have the same length")
    if len(rising_edges.indices) < 2:
        raise WaveformAnalysisError("at least two rising edges are required")
    cycles: list[SwitchingCycle] = []
    for start_index, end_index in zip(
        rising_edges.indices,
        rising_edges.indices[1:],
        strict=False,
    ):
        if start_index < 0 or end_index >= len(time) or start_index >= end_index:
            raise WaveformSchemaError("edge indices must be ordered and within the time array")
        duration = float(time[end_index] - time[start_index])
        if not np.isfinite(duration) or duration <= 0.0:
            raise WaveformAnalysisError("switching cycle duration must be positive")
        cycles.append(
            SwitchingCycle(
                start_index=start_index,
                end_index=end_index,
                start_time=float(time[start_index]),
                end_time=float(time[end_index]),
                duration=duration,
            )
        )
    return tuple(cycles)
