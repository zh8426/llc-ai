import csv
import io
from collections.abc import Iterable

import numpy as np

from app.waveform.exceptions import WaveformSchemaError, WaveformTooLargeError
from app.waveform.limits import MAX_WAVEFORM_CHANNELS, MAX_WAVEFORM_SAMPLES
from app.waveform.models import WaveformData, WaveformMetadata
from app.waveform.preprocessing import (
    finite_sample_mask,
    normalize_channel,
    normalize_time,
    require_strictly_increasing_time,
)

REQUIRED_CHANNELS = ("VGS_Q1", "VDS_Q1", "IRES")
REQUIRED_COLUMNS = ("time", *REQUIRED_CHANNELS)
CHANNEL_TARGET_UNITS = {
    "VGS_Q1": "V",
    "VDS_Q1": "V",
    "IRES": "A",
    "VGS_Q2": "V",
    "VDS_Q2": "V",
    "VBUS": "V",
    "VOUT": "V",
}


def load_waveform_csv(csv_text: str, metadata: WaveformMetadata) -> WaveformData:
    """Parse CSV text and return finite samples normalized to SI boundary units."""

    reader = csv.DictReader(io.StringIO(csv_text))
    fieldnames = reader.fieldnames
    if fieldnames is None:
        raise WaveformSchemaError("CSV must include a header row")
    normalized_headers = tuple(name.strip() for name in fieldnames)
    if normalized_headers != tuple(fieldnames):
        raise WaveformSchemaError("CSV column names must not contain surrounding whitespace")
    if len(set(normalized_headers)) != len(normalized_headers):
        raise WaveformSchemaError("CSV column names must be unique")
    channel_count = len(normalized_headers) - (1 if "time" in normalized_headers else 0)
    if channel_count > MAX_WAVEFORM_CHANNELS:
        raise WaveformTooLargeError(
            "WAVEFORM_TOO_LARGE: CSV channel count exceeds "
            f"the maximum of {MAX_WAVEFORM_CHANNELS}"
        )
    if len(metadata.channels) > MAX_WAVEFORM_CHANNELS:
        raise WaveformTooLargeError(
            "WAVEFORM_TOO_LARGE: channel metadata exceeds "
            f"the maximum of {MAX_WAVEFORM_CHANNELS}"
        )
    missing_columns = [name for name in REQUIRED_COLUMNS if name not in normalized_headers]
    if missing_columns:
        raise WaveformSchemaError(
            f"CSV is missing required columns: {', '.join(missing_columns)}"
        )
    missing_metadata = [name for name in REQUIRED_CHANNELS if name not in metadata.channels]
    if missing_metadata:
        raise WaveformSchemaError(
            f"metadata is missing required channels: {', '.join(missing_metadata)}"
        )

    parsed_columns: dict[str, list[float]] = {
        name: [] for name in normalized_headers if name in {"time", *CHANNEL_TARGET_UNITS}
    }
    sample_count = 0
    for row_number, row in enumerate(reader, start=2):
        if sample_count >= MAX_WAVEFORM_SAMPLES:
            raise WaveformTooLargeError(
                "WAVEFORM_TOO_LARGE: sample count exceeds "
                f"the maximum of {MAX_WAVEFORM_SAMPLES}"
            )
        sample_count += 1
        if None in row:
            raise WaveformSchemaError(f"CSV row {row_number} contains extra values")
        for name in parsed_columns:
            raw_value = row.get(name)
            if raw_value is None or not raw_value.strip():
                parsed_columns[name].append(float("nan"))
                continue
            try:
                parsed_columns[name].append(float(raw_value))
            except ValueError as error:
                raise WaveformSchemaError(
                    f"CSV row {row_number} column {name} must be numeric"
                ) from error

    _require_equal_nonempty_columns(parsed_columns.values())
    raw_time = np.asarray(parsed_columns.pop("time"), dtype=np.float64)
    raw_channels = {
        name: np.asarray(values, dtype=np.float64)
        for name, values in parsed_columns.items()
    }
    loaded_channel_names = [name for name in raw_channels if name in metadata.channels]
    arrays_for_validity = [raw_time, *(raw_channels[name] for name in loaded_channel_names)]
    mask = finite_sample_mask(*arrays_for_validity)
    discarded_samples = int(len(raw_time) - np.count_nonzero(mask))
    time = normalize_time(raw_time[mask], metadata.time_unit)
    require_strictly_increasing_time(time)

    channels: dict[str, np.ndarray] = {}
    for name, values in raw_channels.items():
        channel_metadata = metadata.channels.get(name)
        if channel_metadata is None:
            continue
        channels[name] = normalize_channel(
            name=name,
            values=values[mask],
            metadata=channel_metadata,
            target_unit=CHANNEL_TARGET_UNITS[name],
        )

    return WaveformData(
        time=time,
        channels=channels,
        normalized_channel_units={name: CHANNEL_TARGET_UNITS[name] for name in channels},
        metadata=metadata,
        discarded_samples=discarded_samples,
    )


def _require_equal_nonempty_columns(columns: Iterable[list[float]]) -> None:
    lengths = {len(column) for column in columns}
    if not lengths or lengths == {0}:
        raise WaveformSchemaError("CSV must contain sample rows")
    if len(lengths) != 1:
        raise WaveformSchemaError("CSV columns must contain the same number of samples")
