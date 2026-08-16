from typing import Annotated, cast

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.database import get_session
from app.llm.guardrails import LLMGuardrailError
from app.llm.orchestrator import orchestrate
from app.llm.provider import LLMNotConfiguredError, LLMProviderError
from app.llm.schemas import (
    LLMOrchestrationRequest,
    LLMOrchestrationResponse,
    LLMToolCatalogItem,
    LLMToolCatalogResponse,
)
from app.llm.tools import ToolRegistry

router = APIRouter(prefix="/llm", tags=["llm"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("/tools", response_model=LLMToolCatalogResponse)
def get_llm_tools(session: SessionDependency) -> LLMToolCatalogResponse:
    registry = ToolRegistry(session)
    return LLMToolCatalogResponse(
        tools=tuple(
            LLMToolCatalogItem(
                name=cast(str, tool["name"]),
                description=cast(str, tool["description"]),
                parameters=cast(dict[str, object], tool["parameters"]),
            )
            for tool in registry.catalog()
        )
    )


@router.post(
    "/orchestrate",
    response_model=LLMOrchestrationResponse,
    status_code=status.HTTP_200_OK,
    summary="Run the guarded LLM engineering orchestrator",
)
def post_llm_orchestration(
    payload: LLMOrchestrationRequest,
    session: SessionDependency,
) -> LLMOrchestrationResponse:
    try:
        return orchestrate(session, payload)
    except LLMNotConfiguredError as error:
        raise APIError(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "LLM_NOT_CONFIGURED",
            "LLM 编排尚未启用，请配置 OPENAI_API_KEY 和 LLM_ENABLED=true。",
        ) from error
    except LLMGuardrailError as error:
        raise APIError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "LLM_OUTPUT_INVALID",
            "LLM 输出未通过工程证据或单位校验。",
            details={"reason": str(error)},
        ) from error
    except LLMProviderError as error:
        raise APIError(
            status.HTTP_502_BAD_GATEWAY,
            "LLM_PROVIDER_ERROR",
            "LLM Provider 未返回有效的结构化结果。",
            details={"reason": str(error)},
        ) from error
