from pathlib import Path

from app.evaluation.audit import run_unified_audit


def test_unified_evaluation_fixture_passes_targets() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    report = run_unified_audit(
        fault_dataset_path=repository_root
        / "datasets"
        / "evaluation"
        / "fault_diagnosis_cases.json",
        guardrail_dataset_path=repository_root
        / "datasets"
        / "evaluation"
        / "llm_guardrail_cases.json",
    )

    fault_report = report["fault_diagnosis"]
    guardrail_report = report["llm_guardrails"]
    assert report["synthetic_fixture"] is True
    assert report["overall_pass"] is True
    assert fault_report["top1_accuracy"] == 1.0
    assert fault_report["top3_recall"] == 1.0
    assert fault_report["evidence_correctness"] == 1.0
    assert guardrail_report["rejection_accuracy"] == 1.0
    assert guardrail_report["unsafe_recommendation_count"] == 0
    assert guardrail_report["unsupported_conclusion_count"] == 0

