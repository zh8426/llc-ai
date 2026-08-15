from app.waveform.cycles import segment_cycles
from app.waveform.edges import detect_falling_edges, detect_rising_edges
from app.waveform.features import (
    calculate_peak,
    calculate_rms,
    calculate_switching_frequency,
)
from app.waveform.loader import load_waveform_csv
from app.waveform.models import (
    ChannelFeatureSummary,
    WaveformAnalysisResult,
    WaveformMetadata,
)


def analyze_waveform_csv(
    csv_text: str,
    metadata: WaveformMetadata,
    *,
    gate_low_threshold: float | None = None,
    gate_high_threshold: float | None = None,
) -> WaveformAnalysisResult:
    """Run the complete deterministic Phase 5 pipeline for one CSV waveform."""

    waveform = load_waveform_csv(csv_text, metadata)
    gate = waveform.channels["VGS_Q1"]
    rising_edges = detect_rising_edges(
        waveform.time,
        gate,
        low_threshold=gate_low_threshold,
        high_threshold=gate_high_threshold,
    )
    falling_edges = detect_falling_edges(
        waveform.time,
        gate,
        low_threshold=gate_low_threshold,
        high_threshold=gate_high_threshold,
    )
    cycles = segment_cycles(waveform.time, rising_edges)
    switching_frequency = calculate_switching_frequency(cycles)
    channel_features = {
        name: ChannelFeatureSummary(
            peak=calculate_peak(values, unit=waveform.normalized_channel_units[name]),
            rms=calculate_rms(
                values,
                unit=waveform.normalized_channel_units[name],
                time=waveform.time,
            ),
        )
        for name, values in waveform.channels.items()
    }
    return WaveformAnalysisResult(
        sample_count=len(waveform.time),
        discarded_samples=waveform.discarded_samples,
        rising_edges=rising_edges,
        falling_edges=falling_edges,
        cycles=cycles,
        switching_frequency=switching_frequency,
        channel_features=channel_features,
    )
