"""Run the repository's reproducible cross-phase evaluation fixtures.

The fixtures and metrics in this module are software quality checks only. They
are not an engineering reference design, a safety certification, or a
replacement for engineer review.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.diagnosis.engine import CandidateCase, rank_candidate_cases
from app.llm.guardrails import LLMGuardrailError, validate_final_output
from app.llm.schemas import LLMFinalOutput
from app.schemas.fault_case import FaultSymptom

_TOP3_RECALL_TARGET = 0.80
_EVIDENCE_CORRECTNESS_TARGET = 0.95


class FaultFixtureCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    symptom: FaultSymptom
    observed_features: tuple[str, ...] = Field(min_length=1)
    root_cause: str = Field(min_length=1)
    verification_steps: tuple[str, ...] = Field(min_length=1)
    fix: tuple[str, ...] = Field(min_length=1)
    engineer_verified: bool


class FaultFixtureScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(min_length=1)
    symptom: FaultSymptom
    observed_features: tuple[str, ...] = Field(min_length=1)
    waveform_features: tuple[str, ...] = Field(default=())
    expected_case_ids: tuple[str, ...] = Field(min_length=1)
    expected_evidence_tokens: tuple[str, ...] = Field(min_length=1)


class FaultFixtureDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(min_length=1)
    synthetic_fixture: bool
    disclaimer: str = Field(min_length=1)
    cases: tuple[FaultFixtureCase, ...] = Field(min_length=1)
    scenarios: tuple[FaultFixtureScenario, ...] = Field(min_length=1)


class GuardrailFixtureCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    payload: dict[str, object]
    expected: Literal["accept", "reject"]


class GuardrailFixtureDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(min_length=1)
    synthetic_fixture: bool
    disclaimer: str = Field(min_length=1)
    cases: tuple[GuardrailFixtureCase, ...] = Field(min_length=1)


def run_unified_audit(
    *,
    fault_dataset_path: Path,
    guardrail_dataset_path: Path,
) -> dict[str, object]:
    """Load both fixtures and return a JSON-serializable audit report."""

    fault_dataset = _load_model(fault_dataset_path, FaultFixtureDataset)
    guardrail_dataset = _load_model(guardrail_dataset_path, GuardrailFixtureDataset)
    fault_report = _audit_fault_diagnosis(fault_dataset)
    guardrail_report = _audit_guardrails(guardrail_dataset)
    overall_pass = bool(
        cast(float, fault_report["top3_recall"]) >= _TOP3_RECALL_TARGET
        and cast(float, fault_report["evidence_correctness"])
        >= _EVIDENCE_CORRECTNESS_TARGET
        and cast(float, guardrail_report["rejection_accuracy"]) == 1.0
        and guardrail_report["unsafe_recommendation_count"] == 0
        and guardrail_report["unsupported_conclusion_count"] == 0
    )
    return {
        "synthetic_fixture": fault_dataset.synthetic_fixture
        and guardrail_dataset.synthetic_fixture,
        "disclaimer": (
            "Software evaluation metrics only; not an engineering reference design, "
            "safety certification, or production approval."
        ),
        "targets": {
            "top3_recall_min": _TOP3_RECALL_TARGET,
            "evidence_correctness_min": _EVIDENCE_CORRECTNESS_TARGET,
            "unsafe_recommendation_count": 0,
            "unsupported_conclusion_count": 0,
        },
        "fault_diagnosis": fault_report,
        "llm_guardrails": guardrail_report,
        "overall_pass": overall_pass,
    }


def _audit_fault_diagnosis(dataset: FaultFixtureDataset) -> dict[str, object]:
    cases_by_id = {case.case_id: case for case in dataset.cases}
    verified_cases = tuple(
        _to_candidate(case) for case in dataset.cases if case.engineer_verified
    )
    scenario_results: list[dict[str, object]] = []
    top1_correct_count = 0
    top3_recall_total = 0.0
    evidence_correct_count = 0

    for scenario in dataset.scenarios:
        expected_ids = set(scenario.expected_case_ids)
        missing_ids = expected_ids - cases_by_id.keys()
        if missing_ids:
            raise ValueError(
                f"{scenario.scenario_id} references unknown fixture cases: "
                f"{sorted(missing_ids)}"
            )
        unverified_ids = {
            case_id for case_id in expected_ids if not cases_by_id[case_id].engineer_verified
        }
        if unverified_ids:
            raise ValueError(
                f"{scenario.scenario_id} references unverified fixture cases: "
                f"{sorted(unverified_ids)}"
            )

        candidates = tuple(
            case
            for case in verified_cases
            if cases_by_id[case.case_id].symptom == scenario.symptom
        )
        ranked = rank_candidate_cases(
            candidates,
            observed_features=scenario.observed_features,
            waveform_features=scenario.waveform_features,
            limit=3,
        )
        ranked_ids = [item.case.case_id for item in ranked]
        top1_correct = bool(ranked_ids and ranked_ids[0] in expected_ids)
        top3_recall = len(expected_ids & set(ranked_ids)) / len(expected_ids)
        matched_tokens: set[str] = set()
        if ranked:
            matched_tokens.update(ranked[0].observed_match_tokens)
            matched_tokens.update(ranked[0].waveform_match_tokens)
        expected_tokens = {token.casefold() for token in scenario.expected_evidence_tokens}
        evidence_correct = expected_tokens.issubset(matched_tokens)

        top1_correct_count += int(top1_correct)
        top3_recall_total += top3_recall
        evidence_correct_count += int(evidence_correct)
        scenario_results.append(
            {
                "scenario_id": scenario.scenario_id,
                "expected_case_ids": sorted(expected_ids),
                "ranked_case_ids": ranked_ids,
                "top1_correct": top1_correct,
                "top3_recall": top3_recall,
                "evidence_correct": evidence_correct,
                "matched_evidence_tokens": sorted(matched_tokens),
            }
        )

    scenario_count = len(dataset.scenarios)
    return {
        "scenario_count": scenario_count,
        "case_count": len(dataset.cases),
        "verified_case_count": len(verified_cases),
        "top1_accuracy": top1_correct_count / scenario_count,
        "top3_recall": top3_recall_total / scenario_count,
        "evidence_correctness": evidence_correct_count / scenario_count,
        "scenario_results": scenario_results,
    }


def _audit_guardrails(dataset: GuardrailFixtureDataset) -> dict[str, object]:
    case_results: list[dict[str, object]] = []
    correct_count = 0
    unsafe_recommendation_count = 0
    unsupported_conclusion_count = 0

    for case in dataset.cases:
        actual = "accept"
        rejection_reason: str | None = None
        try:
            output = LLMFinalOutput.model_validate(case.payload)
            validate_final_output(output)
        except (LLMGuardrailError, ValidationError) as error:
            actual = "reject"
            rejection_reason = str(error)

        correct = actual == case.expected
        correct_count += int(correct)
        if case.category == "unsafe_recommendation" and actual == "accept":
            unsafe_recommendation_count += 1
        if case.category == "unsupported_conclusion" and actual == "accept":
            unsupported_conclusion_count += 1
        case_results.append(
            {
                "case_id": case.case_id,
                "category": case.category,
                "expected": case.expected,
                "actual": actual,
                "correct": correct,
                "rejection_reason": rejection_reason,
            }
        )

    case_count = len(dataset.cases)
    return {
        "case_count": case_count,
        "accepted_count": sum(item["actual"] == "accept" for item in case_results),
        "rejected_count": sum(item["actual"] == "reject" for item in case_results),
        "rejection_accuracy": correct_count / case_count,
        "unsafe_recommendation_count": unsafe_recommendation_count,
        "unsupported_conclusion_count": unsupported_conclusion_count,
        "case_results": case_results,
    }


def _to_candidate(case: FaultFixtureCase) -> CandidateCase:
    return CandidateCase(
        case_id=case.case_id,
        root_cause=case.root_cause,
        observed_features=case.observed_features,
        verification_steps=case.verification_steps,
        fix=case.fix,
        waveform_references=(),
        created_at_sort_key=case.case_id,
    )


def _load_model[ModelT: BaseModel](path: Path, model_type: type[ModelT]) -> ModelT:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ValueError(f"unable to read evaluation fixture: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON evaluation fixture: {path}") from error
    return model_type.model_validate(payload)


def _default_fixture_paths() -> tuple[Path, Path]:
    repository_root = Path(__file__).resolve().parents[3]
    fixture_root = repository_root / "datasets" / "evaluation"
    return (
        fixture_root / "fault_diagnosis_cases.json",
        fixture_root / "llm_guardrail_cases.json",
    )


def main(argv: list[str] | None = None) -> int:
    default_fault_path, default_guardrail_path = _default_fixture_paths()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fault-dataset", type=Path, default=default_fault_path)
    parser.add_argument("--guardrail-dataset", type=Path, default=default_guardrail_path)
    args = parser.parse_args(argv)
    report = run_unified_audit(
        fault_dataset_path=args.fault_dataset,
        guardrail_dataset_path=args.guardrail_dataset,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
