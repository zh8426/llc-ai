import json
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import TypeAdapter, ValidationError

from app.schemas.waveform import (
    DeadTimeEvidenceResponse,
    DeadTimeResponse,
    TurnOnEvidenceResponse,
    VDSAtTurnOnResponse,
    WaveformChannelMetadataInput,
    WaveformFrequencyResponse,
    ZVSAnalysisResponse,
)
from app.waveform import (
    ChannelMetadata,
    WaveformMetadata,
    ZVSAnalyzerConfig,
    analyze_zvs_csv,
)
from app.waveform.exceptions import WaveformError
from app.waveform.zvs import ZVSAnalysisResult

router = APIRouter(prefix="/waveforms", tags=["waveforms"])
_CHANNEL_METADATA_ADAPTER = TypeAdapter(dict[str, WaveformChannelMetadataInput])
_TEST_CONDITION_ADAPTER = TypeAdapter(dict[str, str])


@router.post(
    "/zvs",
    response_model=ZVSAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze one CSV waveform for conservative ZVS features",
)
async def post_waveform_zvs(
    file: Annotated[UploadFile, File(description="CSV with time, VGS_Q1, VDS_Q1, IRES")],
    sample_rate: Annotated[float, Form(gt=0)],
    channels: Annotated[str, Form(description="JSON channel metadata mapping")],
    test_condition: Annotated[str, Form(description="JSON test condition mapping")],
    vds_zvs_threshold: Annotated[float, Form(ge=0)],
    vds_hard_switching_threshold: Annotated[float, Form(gt=0)],
    time_unit: Annotated[str, Form()] = "s",
    gate_low_threshold: Annotated[float | None, Form()] = None,
    gate_high_threshold: Annotated[float | None, Form()] = None,
) -> ZVSAnalysisResponse:
    try:
        csv_bytes = await file.read()
        csv_text = csv_bytes.decode("utf-8-sig")
        channel_payload = _parse_json_form(channels, _CHANNEL_METADATA_ADAPTER)
        test_condition_payload = _parse_json_form(test_condition, _TEST_CONDITION_ADAPTER)
        metadata = WaveformMetadata(
            sample_rate=sample_rate,
            time_unit=time_unit,
            channels={
                name: ChannelMetadata(
                    unit=channel.unit,
                    probe_ratio=channel.probe_ratio,
                    polarity=channel.polarity,
                    bandwidth_hz=channel.bandwidth_hz,
                )
                for name, channel in channel_payload.items()
            },
            test_condition=test_condition_payload,
        )
        result = analyze_zvs_csv(
            csv_text,
            metadata,
            ZVSAnalyzerConfig(
                vds_zvs_threshold=vds_zvs_threshold,
                vds_hard_switching_threshold=vds_hard_switching_threshold,
                gate_low_threshold=gate_low_threshold,
                gate_high_threshold=gate_high_threshold,
            ),
        )
    except (UnicodeDecodeError, ValidationError, WaveformError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    return _zvs_to_response(result)


def _parse_json_form(value: str, adapter: TypeAdapter[Any]) -> Any:
    return adapter.validate_python(json.loads(value))


def _zvs_to_response(result: ZVSAnalysisResult) -> ZVSAnalysisResponse:
    frequency = result.switching_frequency
    return ZVSAnalysisResponse(
        switching_frequency=(
            None
            if frequency is None
            else WaveformFrequencyResponse(
                value=frequency.value,
                unit="Hz",
                cycle_count=frequency.cycle_count,
                formula_version=frequency.formula_version,
            )
        ),
        dead_time=DeadTimeResponse(
            value=result.dead_time.value,
            values=result.dead_time.values,
            evidence=tuple(
                DeadTimeEvidenceResponse(
                    primary_turn_off_time=item.primary_turn_off_time,
                    complementary_turn_on_time=item.complementary_turn_on_time,
                    duration=item.duration,
                )
                for item in result.dead_time.evidence
            ),
            unit="s",
            status=result.dead_time.status,
            formula_version=result.dead_time.formula_version,
        ),
        vds_at_turn_on=(
            None
            if result.vds_at_turn_on is None
            else VDSAtTurnOnResponse(
                value=result.vds_at_turn_on.value,
                values=result.vds_at_turn_on.values,
                unit="V",
                formula_version=result.vds_at_turn_on.formula_version,
            )
        ),
        zvs_status=result.zvs_status,
        confidence=result.confidence,
        evidence_cycles=tuple(
            TurnOnEvidenceResponse(
                cycle_index=item.cycle_index,
                gate_turn_on_time=item.gate_turn_on_time,
                vds_at_turn_on=item.vds_at_turn_on,
                ires_at_turn_on=item.ires_at_turn_on,
                status=item.status,
            )
            for item in result.evidence_cycles
        ),
        limitations=result.limitations,
        analysis_version=result.analysis_version,
        gate_turn_on_timestamps=result.gate_turn_on_timestamps,
        gate_turn_off_timestamps=result.gate_turn_off_timestamps,
    )
