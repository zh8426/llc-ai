from sqlalchemy.orm import Session

from app.llm.guardrails import validate_final_output
from app.llm.provider import (
    LLMProvider,
    ProviderResult,
    build_provider,
)
from app.llm.schemas import (
    LLMOrchestrationRequest,
    LLMOrchestrationResponse,
)
from app.llm.tools import ToolRegistry


def orchestrate(
    session: Session,
    payload: LLMOrchestrationRequest,
    *,
    provider: LLMProvider | None = None,
) -> LLMOrchestrationResponse:
    active_provider = provider or build_provider()
    registry = ToolRegistry(session, allowed_project_id=payload.project_id)
    result: ProviderResult = active_provider.generate(payload.message, registry)
    output = validate_final_output(result.output)
    return LLMOrchestrationResponse(
        summary=output.summary,
        claims=output.claims,
        evidence=output.evidence,
        missing_information=output.missing_information,
        next_actions=output.next_actions,
        requires_engineer_confirmation=output.requires_engineer_confirmation,
        tool_calls=result.tool_calls,
        provider=result.provider,
        model=result.model,
    )
