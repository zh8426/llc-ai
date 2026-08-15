from math import isfinite

import numpy as np
from numpy.typing import NDArray
from pint import UnitRegistry
from pint.errors import PintError

from app.waveform.exceptions import WaveformSchemaError
from app.waveform.models import ChannelMetadata

_UNIT_REGISTRY: UnitRegistry = UnitRegistry()


def normalize_time(values: NDArray[np.float64], unit: str) -> NDArray[np.float64]:
    return _convert_array(values, source_unit=unit, target_unit="s", name="time")


def normalize_channel(
    *,
    name: str,
    values: NDArray[np.float64],
    metadata: ChannelMetadata,
    target_unit: str,
) -> NDArray[np.float64]:
    converted = _convert_array(
        values,
        source_unit=metadata.unit,
        target_unit=target_unit,
        name=name,
    )
    with np.errstate(over="ignore", invalid="ignore"):
        normalized = converted * metadata.probe_ratio * metadata.polarity
    if not np.all(np.isfinite(normalized)):
        raise WaveformSchemaError(f"{name} normalization must produce finite samples")
    return normalized


def finite_sample_mask(*arrays: NDArray[np.float64]) -> NDArray[np.bool_]:
    if not arrays:
        raise WaveformSchemaError("at least one sample array is required")
    sample_count = len(arrays[0])
    if any(len(array) != sample_count for array in arrays):
        raise WaveformSchemaError("all waveform arrays must have the same length")
    mask = np.ones(sample_count, dtype=np.bool_)
    for array in arrays:
        mask &= np.isfinite(array)
    return mask


def require_strictly_increasing_time(time: NDArray[np.float64]) -> None:
    if len(time) < 2:
        raise WaveformSchemaError("waveform must contain at least two valid samples")
    if not np.all(np.diff(time) > 0.0):
        raise WaveformSchemaError("time samples must be strictly increasing")


def _convert_array(
    values: NDArray[np.float64],
    *,
    source_unit: str,
    target_unit: str,
    name: str,
) -> NDArray[np.float64]:
    if not source_unit.strip():
        raise WaveformSchemaError(f"{name} unit must not be empty")
    try:
        scale = float(_UNIT_REGISTRY.Quantity(1.0, source_unit).to(target_unit).magnitude)
    except (PintError, TypeError, ValueError) as error:
        raise WaveformSchemaError(
            f"{name} must use a unit compatible with {target_unit}; received {source_unit!r}"
        ) from error
    if not isfinite(scale):
        raise WaveformSchemaError(f"{name} unit conversion must be finite")
    with np.errstate(over="ignore", invalid="ignore"):
        converted = values.astype(np.float64, copy=False) * scale
    if not np.all(np.isfinite(converted)):
        raise WaveformSchemaError(f"{name} unit conversion must produce finite samples")
    return converted
