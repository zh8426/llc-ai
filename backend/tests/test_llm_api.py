import httpx
import pytest

from app.llm.orchestrator import orchestrate
from app.llm.provider import ProviderResult
from app.llm.schemas import (
    LLMClaim,
    LLMEvidence,
    LLMEvidenceSource,
    LLMFinalOutput,
    LLMOrchestrationRequest,
    LLMToolCallRecord,
)
from app.llm.tools import ToolRegistry


class FakeProvider:
    def generate(self, message: str, registry: ToolRegistry) -> ProviderResult:
        result = registry.execute(
            "calculate_resonant_tank",
            {
                "lr": {"value": 45, "unit": "uH"},
                "lm": {"value": 300, "unit": "uH"},
                "cr": {"value": 47, "unit": "nF"},
            },
        )
        assert result["calculations"]
        output = LLMFinalOutput(
            summary="The calculation tool returned a structured result.",
            claims=(
                LLMClaim(
                    claim_id="C001",
                    text="The resonant-tank calculations were obtained from the deterministic tool.",
                    evidence_refs=("E001",),
                ),
            ),
            evidence=(
                LLMEvidence(
                    evidence_id="E001",
                    source=LLMEvidenceSource.CALCULATION,
                    description="Deterministic resonant-tank tool output.",
                    references=("LLC-FR-V1", "LLC-FP-V1"),
                ),
            ),
            missing_information=(),
            next_actions=(),
            requires_engineer_confirmation=False,
        )
        return ProviderResult(
            output=output,
            tool_calls=(
                LLMToolCallRecord(
                    name="calculate_resonant_tank",
                    arguments={"unit_checked": True},
                    status="completed",
                ),
            ),
            provider="fake",
            model="fake-model",
        )


@pytest.mark.anyio
async def test_llm_tools_catalog_exposes_workflow_tools(
    api_client: httpx.AsyncClient,
) -> None:
    response = await api_client.get("/llm/tools")

    assert response.status_code == 200
    names = {item["name"] for item in response.json()["tools"]}
    assert names == {
        "get_project",
        "calculate_resonant_tank",
        "run_design_review",
        "get_component_parameter",
        "analyze_waveform",
        "run_zvs_check",
        "find_similar_fault_cases",
        "search_engineering_evidence",
        "generate_review_report",
    }


@pytest.mark.anyio
async def test_llm_endpoint_is_disabled_without_explicit_configuration(
    api_client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_ENABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    response = await api_client.post(
        "/llm/orchestrate",
        json={"message": "请分析当前项目，但不要猜测缺失参数。"},
    )

    assert response.status_code == 503
    assert response.json()["code"] == "LLM_NOT_CONFIGURED"


def test_orchestrator_uses_fake_provider_without_network(
    api_session_factory,
) -> None:
    with api_session_factory() as session:
        response = orchestrate(
            session,
            LLMOrchestrationRequest(message="Calculate the resonant tank."),
            provider=FakeProvider(),
        )

    assert response.provider == "fake"
    assert response.tool_calls[0].name == "calculate_resonant_tank"
    assert response.claims[0].evidence_refs == ("E001",)
