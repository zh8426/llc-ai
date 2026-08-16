import json
import os
from dataclasses import dataclass
from typing import Any, Protocol

from app.llm.guardrails import LLMGuardrailError, validate_final_output
from app.llm.schemas import LLMFinalOutput, LLMToolCallRecord
from app.llm.tools import ToolExecutionError, ToolRegistry


class LLMNotConfiguredError(RuntimeError):
    """Raised when the explicit LLM feature flag or API key is absent."""


class LLMProviderError(RuntimeError):
    """Raised when an enabled provider cannot return valid structured output."""


@dataclass(frozen=True)
class ProviderResult:
    output: LLMFinalOutput
    tool_calls: tuple[LLMToolCallRecord, ...]
    provider: str
    model: str


class LLMProvider(Protocol):
    def generate(self, message: str, registry: ToolRegistry) -> ProviderResult:
        """Generate one guarded structured orchestration result."""


SYSTEM_PROMPT = """You are an engineering orchestration layer for a Half-Bridge LLC assistant.

Mandatory rules:
1. Never replace deterministic calculations, waveform analysis, unit validation, or Design
   Review rules with your own arithmetic. Call the corresponding tool.
2. Read project parameters, Datasheet values, Reviews, Waveform results, and FaultCases only
   through tools. Do not invent missing parameters or units.
3. Only use evidence returned by tools. Every claim must cite one or more evidence_id values.
4. Never call an estimated value measured, a simulation measured, or a human-unverified
   Datasheet parameter verified.
5. Never state that a design is safe, certified, production-ready, or approved. Safety-related
   discussion must include evidence and requires_engineer_confirmation=true.
6. If evidence or units are missing, list them in missing_information and do not fill them in.
7. Tools are read-only for this orchestration request. Do not repeat completed calls.

Return exactly the requested JSON schema. Keep claims concise and traceable.
"""


class OpenAIResponsesProvider:
    provider_name = "openai-responses"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        max_tool_rounds: int = 4,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.max_tool_rounds = max_tool_rounds
        self.base_url = base_url

    def generate(self, message: str, registry: ToolRegistry) -> ProviderResult:
        try:
            from openai import OpenAI
        except ImportError as error:
            raise LLMProviderError(
                "The openai package is required when LLM_ENABLED=true."
            ) from error

        client_kwargs: dict[str, object] = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        openai_client_class: Any = OpenAI
        client = openai_client_class(**client_kwargs)
        input_items: list[object] = [{"role": "user", "content": message}]
        tool_calls: list[LLMToolCallRecord] = []
        for _ in range(self.max_tool_rounds + 1):
            try:
                response = client.responses.create(
                    model=self.model,
                    instructions=SYSTEM_PROMPT,
                    input=input_items,
                    tools=list(registry.openai_tools()),
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "llm_final_output",
                            "schema": LLMFinalOutput.model_json_schema(),
                            "strict": True,
                        }
                    },
                    store=False,
                )
            except Exception as error:  # provider SDK errors vary by version
                raise LLMProviderError("OpenAI Responses request failed.") from error

            output_items = list(getattr(response, "output", ()))
            function_calls = [
                item for item in output_items if getattr(item, "type", None) == "function_call"
            ]
            if not function_calls:
                return self._parse_final_response(response, tool_calls)
            if len(tool_calls) + len(function_calls) > self.max_tool_rounds:
                raise LLMProviderError("LLM tool-call round limit exceeded.")

            input_items.extend(_serialize_output_item(item) for item in output_items)
            for call in function_calls:
                name = str(getattr(call, "name", ""))
                raw_arguments = str(getattr(call, "arguments", "{}"))
                try:
                    arguments = json.loads(raw_arguments)
                    if not isinstance(arguments, dict):
                        raise ValueError("tool arguments must be an object")
                    result = registry.execute(name, arguments)
                    status = "completed"
                except (ValueError, ToolExecutionError) as error:
                    arguments = _safe_arguments(raw_arguments)
                    result = {"error": str(error)}
                    status = "rejected"
                call_id = str(getattr(call, "call_id", ""))
                tool_calls.append(
                    LLMToolCallRecord(name=name, arguments=arguments, status=status)
                )
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(result, ensure_ascii=False),
                    }
                )
        raise LLMProviderError("LLM did not return a final structured output.")

    def _parse_final_response(
        self, response: object, tool_calls: list[LLMToolCallRecord]
    ) -> ProviderResult:
        raw_text = str(getattr(response, "output_text", ""))
        try:
            output = validate_final_output(LLMFinalOutput.model_validate(json.loads(raw_text)))
        except (json.JSONDecodeError, TypeError, ValueError, LLMGuardrailError) as error:
            raise LLMProviderError("LLM output failed the structured engineering contract.") from error
        return ProviderResult(
            output=output,
            tool_calls=tuple(tool_calls),
            provider=self.provider_name,
            model=self.model,
        )


def build_provider() -> OpenAIResponsesProvider:
    enabled = os.getenv("LLM_ENABLED", "false").strip().casefold() == "true"
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not enabled or not api_key:
        raise LLMNotConfiguredError(
            "Set LLM_ENABLED=true and OPENAI_API_KEY to enable the LLM boundary."
        )
    model = os.getenv("OPENAI_MODEL", "gpt-5.6-terra").strip()
    if not model:
        raise LLMNotConfiguredError("OPENAI_MODEL must not be empty.")
    try:
        max_tool_rounds = int(os.getenv("OPENAI_MAX_TOOL_ROUNDS", "4"))
    except ValueError as error:
        raise LLMNotConfiguredError("OPENAI_MAX_TOOL_ROUNDS must be an integer.") from error
    if not 1 <= max_tool_rounds <= 8:
        raise LLMNotConfiguredError("OPENAI_MAX_TOOL_ROUNDS must be between 1 and 8.")
    return OpenAIResponsesProvider(
        api_key=api_key,
        model=model,
        max_tool_rounds=max_tool_rounds,
        base_url=os.getenv("OPENAI_BASE_URL") or None,
    )


def _serialize_output_item(item: object) -> object:
    model_dump = getattr(item, "model_dump", None)
    if callable(model_dump):
        return model_dump(mode="json")
    return item


def _safe_arguments(raw_arguments: str) -> dict[str, object]:
    try:
        value = json.loads(raw_arguments)
    except json.JSONDecodeError:
        return {"_raw": raw_arguments[:500]}
    return value if isinstance(value, dict) else {"_raw": raw_arguments[:500]}
