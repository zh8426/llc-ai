from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from app.engine import (
    calculate_fp,
    calculate_fr,
    calculate_lm_lr_ratio,
    calculate_zr,
)
from app.models.project import Project
from app.schemas.datasheet import DatasheetParameterName
from app.schemas.diagnosis import FaultSymptom
from app.schemas.engineering import EngineeringQuantity
from app.schemas.project import ProjectResponse
from app.schemas.waveform import WaveformChannelMetadataInput
from app.services.datasheets import get_datasheet_document
from app.services.fault_cases import search_fault_cases
from app.services.projects import get_project, project_to_response
from app.services.reports import render_review_run
from app.services.reviews import (
    build_review_context,
    get_latest_review,
)
from app.waveform import (
    ChannelMetadata,
    WaveformMetadata,
    ZVSAnalyzerConfig,
    analyze_waveform_csv,
    analyze_zvs_csv,
)


class ToolExecutionError(ValueError):
    """Raised when a requested deterministic tool cannot return structured data."""


class ProjectToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(min_length=1, max_length=36)


class ResonantTankToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lr: EngineeringQuantity
    lm: EngineeringQuantity
    cr: EngineeringQuantity


class DatasheetParameterToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1, max_length=36)
    parameter_name: DatasheetParameterName | None = None


class FaultCaseSearchToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=500)
    symptom: FaultSymptom | None = None
    engineer_verified: bool = True
    limit: int = Field(default=3, ge=1, le=20)


class EngineeringEvidenceToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=500)
    project_id: str | None = Field(default=None, min_length=1, max_length=36)
    limit: int = Field(default=5, ge=1, le=20)


class WaveformToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    csv_text: str = Field(min_length=1, max_length=2_000_000)
    sample_rate: float = Field(gt=0, allow_inf_nan=False)
    time_unit: str = Field(default="s", min_length=1, max_length=20)
    channels: dict[str, WaveformChannelMetadataInput] = Field(min_length=1)
    test_condition: dict[str, str] = Field(min_length=1)
    vds_zvs_threshold: float = Field(ge=0, allow_inf_nan=False)
    vds_hard_switching_threshold: float = Field(gt=0, allow_inf_nan=False)
    gate_low_threshold: float | None = Field(default=None, allow_inf_nan=False)
    gate_high_threshold: float | None = Field(default=None, allow_inf_nan=False)


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_model: type[BaseModel]

    def parameters(self) -> dict[str, object]:
        return self.input_model.model_json_schema()


TOOL_DEFINITIONS: tuple[ToolDefinition, ...] = (
    ToolDefinition(
        "get_project",
        "Read one persisted project and its explicit engineering quantities.",
        ProjectToolInput,
    ),
    ToolDefinition(
        "calculate_resonant_tank",
        "Run deterministic fr, fp, Zr, and Lm/Lr calculations from explicit units.",
        ResonantTankToolInput,
    ),
    ToolDefinition(
        "run_design_review",
        "Run the deterministic R001-R020 review without persisting a new review run.",
        ProjectToolInput,
    ),
    ToolDefinition(
        "get_component_parameter",
        "Read extracted MOSFET datasheet parameters and human verification state.",
        DatasheetParameterToolInput,
    ),
    ToolDefinition(
        "analyze_waveform",
        "Run the deterministic Phase 5 waveform feature pipeline on bounded CSV text.",
        WaveformToolInput,
    ),
    ToolDefinition(
        "run_zvs_check",
        "Run the deterministic Phase 6 ZVS analysis with explicit thresholds.",
        WaveformToolInput,
    ),
    ToolDefinition(
        "find_similar_fault_cases",
        "Retrieve structured fault cases with an optional engineer_verified filter.",
        FaultCaseSearchToolInput,
    ),
    ToolDefinition(
        "search_engineering_evidence",
        "Search verified fault cases and optionally the latest project Review findings.",
        EngineeringEvidenceToolInput,
    ),
    ToolDefinition(
        "generate_review_report",
        "Render the latest persisted Design Review report without recalculating it.",
        ProjectToolInput,
    ),
)


class ToolRegistry:
    def __init__(self, session: Session, *, allowed_project_id: str | None = None) -> None:
        self.session = session
        self.allowed_project_id = allowed_project_id
        self._definitions = {definition.name: definition for definition in TOOL_DEFINITIONS}

    def catalog(self) -> tuple[dict[str, object], ...]:
        return tuple(
            {
                "name": definition.name,
                "description": definition.description,
                "parameters": definition.parameters(),
            }
            for definition in TOOL_DEFINITIONS
        )

    def openai_tools(self) -> tuple[dict[str, object], ...]:
        return tuple(
            {
                "type": "function",
                "name": definition.name,
                "description": definition.description,
                "parameters": definition.parameters(),
                "strict": True,
            }
            for definition in TOOL_DEFINITIONS
        )

    def execute(self, name: str, arguments: dict[str, object]) -> dict[str, object]:
        definition = self._definitions.get(name)
        if definition is None:
            raise ToolExecutionError(f"unknown tool: {name}")
        try:
            payload = definition.input_model.model_validate(arguments)
        except ValidationError as error:
            raise ToolExecutionError(f"invalid arguments for {name}: {error}") from error
        handler = getattr(self, f"_handle_{name}")
        try:
            result = handler(payload)
        except ToolExecutionError:
            raise
        except Exception as error:
            raise ToolExecutionError(f"tool {name} failed: {error}") from error
        if isinstance(result, BaseModel):
            return result.model_dump(mode="json")
        if not isinstance(result, dict):
            raise ToolExecutionError(f"tool {name} returned a non-object result")
        return result

    def _require_project(self, project_id: str) -> Project:
        if self.allowed_project_id is not None and project_id != self.allowed_project_id:
            raise ToolExecutionError("tool project_id is outside the requested scope")
        project = get_project(self.session, project_id)
        if project is None:
            raise ToolExecutionError(f"project not found: {project_id}")
        return project

    def _handle_get_project(self, payload: ProjectToolInput) -> ProjectResponse:
        return project_to_response(self._require_project(payload.project_id))

    def _handle_calculate_resonant_tank(
        self, payload: ResonantTankToolInput
    ) -> dict[str, object]:
        return {
            "calculations": [
                result.model_dump(mode="json")
                for result in (
                    calculate_fr(lr=payload.lr, cr=payload.cr),
                    calculate_fp(lr=payload.lr, lm=payload.lm, cr=payload.cr),
                    calculate_zr(lr=payload.lr, cr=payload.cr),
                    calculate_lm_lr_ratio(lr=payload.lr, lm=payload.lm),
                )
            ]
        }

    def _handle_run_design_review(self, payload: ProjectToolInput) -> dict[str, object]:
        from app.rules import run_design_review
        from app.services.calculations import calculate_project

        project = self._require_project(payload.project_id)
        calculation_snapshot = calculate_project(project)
        result = run_design_review(build_review_context(project, calculation_snapshot))
        return result.model_dump(mode="json")

    def _handle_get_component_parameter(
        self, payload: DatasheetParameterToolInput
    ) -> dict[str, object]:
        document = get_datasheet_document(self.session, payload.document_id)
        if document is None:
            raise ToolExecutionError(f"datasheet not found: {payload.document_id}")
        parameters = [
            parameter
            for parameter in document.parameters
            if payload.parameter_name is None
            or parameter.parameter_name == payload.parameter_name.value
        ]
        return {
            "document_id": document.id,
            "parameters": [
                {
                    "id": parameter.id,
                    "parameter_name": parameter.parameter_name,
                    "value": (
                        parameter.value_numeric
                        if parameter.value_numeric is not None
                        else parameter.value_text
                    ),
                    "unit": parameter.unit,
                    "value_type": parameter.value_type,
                    "test_condition": parameter.test_condition,
                    "source_page": parameter.source_page,
                    "confidence": parameter.confidence,
                    "human_verified": parameter.human_verified,
                }
                for parameter in parameters
            ],
        }

    def _handle_analyze_waveform(self, payload: WaveformToolInput) -> dict[str, object]:
        result = analyze_waveform_csv(payload.csv_text, _waveform_metadata(payload))
        return {
            "sample_count": result.sample_count,
            "discarded_samples": result.discarded_samples,
            "switching_frequency": {
                "value": result.switching_frequency.value,
                "unit": result.switching_frequency.unit,
                "cycle_count": result.switching_frequency.cycle_count,
                "formula_version": result.switching_frequency.formula_version,
            },
            "channel_features": {
                name: {
                    "peak": {
                        "name": feature.peak.name,
                        "value": feature.peak.value,
                        "unit": feature.peak.unit,
                        "sample_count": feature.peak.sample_count,
                        "formula_version": feature.peak.formula_version,
                    },
                    "rms": {
                        "name": feature.rms.name,
                        "value": feature.rms.value,
                        "unit": feature.rms.unit,
                        "sample_count": feature.rms.sample_count,
                        "formula_version": feature.rms.formula_version,
                    },
                }
                for name, feature in result.channel_features.items()
            },
            "analysis_version": result.analysis_version,
        }

    def _handle_run_zvs_check(self, payload: WaveformToolInput) -> dict[str, object]:
        result = analyze_zvs_csv(
            payload.csv_text,
            _waveform_metadata(payload),
            ZVSAnalyzerConfig(
                vds_zvs_threshold=payload.vds_zvs_threshold,
                vds_hard_switching_threshold=payload.vds_hard_switching_threshold,
                gate_low_threshold=payload.gate_low_threshold,
                gate_high_threshold=payload.gate_high_threshold,
            ),
        )
        return {
            "zvs_status": result.zvs_status,
            "cycle_consistency": result.cycle_consistency,
            "dead_time": {
                "value": result.dead_time.value,
                "values": result.dead_time.values,
                "status": result.dead_time.status,
                "unit": result.dead_time.unit,
                "valid_cycle_count": result.dead_time.valid_cycle_count,
                "missing_cycle_count": result.dead_time.missing_cycle_count,
                "rejected_cycle_count": result.dead_time.rejected_cycle_count,
            },
            "vds_at_turn_on": (
                None
                if result.vds_at_turn_on is None
                else {
                    "value": result.vds_at_turn_on.value,
                    "values": result.vds_at_turn_on.values,
                    "unit": result.vds_at_turn_on.unit,
                }
            ),
            "limitations": result.limitations,
            "analysis_version": result.analysis_version,
        }

    def _handle_find_similar_fault_cases(
        self, payload: FaultCaseSearchToolInput
    ) -> dict[str, object]:
        results = search_fault_cases(
            self.session,
            query=payload.query,
            symptom=payload.symptom,
            engineer_verified=payload.engineer_verified,
            limit=payload.limit,
        )
        return {
            "cases": [
                {
                    "case_id": case.case_id,
                    "symptom": case.symptom,
                    "root_cause": case.root_cause,
                    "similarity_score": score,
                    "engineer_verified": case.engineer_verified,
                }
                for case, score in results
            ]
        }

    def _handle_search_engineering_evidence(
        self, payload: EngineeringEvidenceToolInput
    ) -> dict[str, object]:
        cases = search_fault_cases(
            self.session,
            query=payload.query,
            engineer_verified=True,
            limit=payload.limit,
        )
        review = (
            get_latest_review(self.session, payload.project_id)
            if payload.project_id is not None
            else None
        )
        return {
            "verified_fault_cases": [
                {
                    "case_id": case.case_id,
                    "symptom": case.symptom,
                    "root_cause": case.root_cause,
                    "similarity_score": score,
                }
                for case, score in cases
            ],
            "review": (
                None
                if review is None
                else {
                    "review_id": review.id,
                    "report_eligible_rule_ids": [
                        finding.rule_id
                        for finding in review.findings
                        if finding.report_eligible
                    ],
                }
            ),
        }

    def _handle_generate_review_report(
        self, payload: ProjectToolInput
    ) -> dict[str, object]:
        project = self._require_project(payload.project_id)
        review = get_latest_review(self.session, project.id)
        if review is None:
            raise ToolExecutionError("project has no persisted Design Review")
        return {"review_id": review.id, "html": render_review_run(review)}


def _waveform_metadata(payload: WaveformToolInput) -> WaveformMetadata:
    return WaveformMetadata(
        sample_rate=payload.sample_rate,
        time_unit=payload.time_unit,
        channels={
            name: ChannelMetadata(
                unit=channel.unit,
                probe_ratio=channel.probe_ratio,
                polarity=channel.polarity,
                bandwidth_hz=channel.bandwidth_hz,
            )
            for name, channel in payload.channels.items()
        },
        test_condition=payload.test_condition,
    )
