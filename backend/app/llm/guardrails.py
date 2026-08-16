import re

from app.llm.schemas import LLMFinalOutput


class LLMGuardrailError(ValueError):
    """Raised when a provider output violates the engineering output contract."""


_SAFETY_LANGUAGE = re.compile(
    r"安全|量产|认证|可直接使用|可以使用|safe|production[- ]ready|certified|approved",
    re.IGNORECASE,
)
_ENGINEERING_LANGUAGE = re.compile(
    r"电压|电流|功率|频率|电感|电容|阻抗|裕量|voltage|current|power|frequency|"
    r"inductance|capacitance|impedance|margin|VDS|VOUT|VIN|IRES",
    re.IGNORECASE,
)
_NUMBER = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?(?![A-Za-z])")
_NUMBER_WITH_UNIT = re.compile(
    r"\d+(?:\.\d+)?\s*(?:V|mV|kV|A|mA|W|kW|Hz|kHz|MHz|H|mH|uH|nH|F|uF|nF|"
    r"ohm|Ω|ns|us|ms|s|%|percent)(?![A-Za-z])",
    re.IGNORECASE,
)


def validate_final_output(output: LLMFinalOutput) -> LLMFinalOutput:
    evidence_ids = [item.evidence_id for item in output.evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise LLMGuardrailError("duplicate evidence_id in LLM output")
    evidence_id_set = set(evidence_ids)
    for claim in output.claims:
        unknown_refs = set(claim.evidence_refs) - evidence_id_set
        if unknown_refs:
            raise LLMGuardrailError(
                f"claim {claim.claim_id} references unknown evidence: {sorted(unknown_refs)}"
            )
        _validate_engineering_units(claim.text)

    safety_text = " ".join([output.summary, *(claim.text for claim in output.claims)])
    if _SAFETY_LANGUAGE.search(safety_text):
        if not output.requires_engineer_confirmation:
            raise LLMGuardrailError(
                "safety-related language requires engineer confirmation"
            )
        if not output.evidence:
            raise LLMGuardrailError(
                "safety-related language requires at least one evidence item"
            )
    return output


def _validate_engineering_units(text: str) -> None:
    if not _ENGINEERING_LANGUAGE.search(text):
        return
    numbers = _NUMBER.findall(text)
    if numbers and len(_NUMBER_WITH_UNIT.findall(text)) < len(numbers):
        raise LLMGuardrailError(
            "engineering numeric claims must include explicit units"
        )
