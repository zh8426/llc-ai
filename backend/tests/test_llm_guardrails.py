import pytest

from app.llm.guardrails import LLMGuardrailError, validate_final_output
from app.llm.schemas import (
    LLMClaim,
    LLMEvidence,
    LLMEvidenceSource,
    LLMFinalOutput,
)


def valid_output(**changes: object) -> LLMFinalOutput:
    payload: dict[str, object] = {
        "summary": "The deterministic calculation tool returned a traceable result.",
        "claims": (
            LLMClaim(
                claim_id="C001",
                text="The resonant frequency is available from the calculation tool.",
                evidence_refs=("E001",),
            ),
        ),
        "evidence": (
            LLMEvidence(
                evidence_id="E001",
                source=LLMEvidenceSource.CALCULATION,
                description="Deterministic resonant-tank calculation.",
                references=("LLC-FR-V1",),
            ),
        ),
        "missing_information": (),
        "next_actions": (),
        "requires_engineer_confirmation": False,
    }
    payload.update(changes)
    return LLMFinalOutput.model_validate(payload)


def test_guardrail_accepts_claims_with_known_evidence() -> None:
    assert validate_final_output(valid_output()).claims[0].evidence_refs == ("E001",)


def test_guardrail_rejects_unknown_evidence_reference() -> None:
    output = valid_output(
        claims=(
            LLMClaim(
                claim_id="C001",
                text="A claim without a matching evidence item.",
                evidence_refs=("E999",),
            ),
        )
    )

    with pytest.raises(LLMGuardrailError, match="unknown evidence"):
        validate_final_output(output)


def test_guardrail_rejects_safety_language_without_confirmation() -> None:
    output = valid_output(
        summary="The design is safe and production-ready.",
        requires_engineer_confirmation=False,
    )

    with pytest.raises(LLMGuardrailError, match="engineer confirmation"):
        validate_final_output(output)


def test_guardrail_rejects_engineering_number_without_unit() -> None:
    output = valid_output(
        claims=(
            LLMClaim(
                claim_id="C001",
                text="The voltage stress is 500 and needs review.",
                evidence_refs=("E001",),
            ),
        )
    )

    with pytest.raises(LLMGuardrailError, match="explicit units"):
        validate_final_output(output)
