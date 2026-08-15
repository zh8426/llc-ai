class WaveformError(ValueError):
    """Base error for deterministic waveform processing failures."""


class WaveformSchemaError(WaveformError):
    """Raised when waveform data or metadata does not satisfy the input contract."""


class WaveformTooLargeError(WaveformError):
    """Raised when waveform analysis exceeds a deterministic resource limit."""


class WaveformAnalysisError(WaveformError):
    """Raised when valid samples are insufficient for a requested feature."""
