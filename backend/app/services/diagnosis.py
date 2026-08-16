from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.diagnosis import CandidateCase, RankedCandidateCase, rank_candidate_cases
from app.models.fault_case import FaultCase
from app.models.project import Project
from app.models.review import ReviewRun
from app.schemas.diagnosis import (
    CandidateCause,
    DiagnosisEvidenceItem,
    DiagnosisEvidenceSource,
    DiagnosisEvidenceSummary,
    FaultDiagnosisRequest,
    FaultDiagnosisResponse,
)
from app.services.fault_cases import list_fault_cases
from app.services.projects import (
    CONTROLLER_QUANTITIES,
    PRIMARY_SWITCH_QUANTITIES,
    PROJECT_QUANTITIES,
    RESONANT_CAPACITOR_QUANTITIES,
    get_project,
)
from app.services.reviews import get_latest_review


def diagnose_fault(
    session: Session, payload: FaultDiagnosisRequest
) -> FaultDiagnosisResponse:
    project = get_project(session, payload.project_id)
    if project is None:
        raise LookupError(payload.project_id)

    review = get_latest_review(session, project.id)
    verified_cases = tuple(
        case
        for case in list_fault_cases(session)
        if case.engineer_verified and case.symptom == payload.symptom.value
    )
    ranked = rank_candidate_cases(
        tuple(
            CandidateCase(
                case_id=case.case_id,
                root_cause=case.root_cause,
                observed_features=tuple(case.observed_features),
                verification_steps=tuple(case.verification_steps),
                fix=tuple(case.fix),
                waveform_references=tuple(
                    reference
                    for reference in (case.waveform_before, case.waveform_after)
                    if reference is not None
                ),
                created_at_sort_key=case.created_at.isoformat(),
            )
            for case in verified_cases
        ),
        observed_features=payload.observed_features,
        waveform_features=payload.waveform_features,
    )
    return FaultDiagnosisResponse(
        symptom=payload.symptom,
        candidate_causes=tuple(
            _candidate_response(item, payload, project, review)
            for item in ranked
        ),
        evidence_summary=_evidence_summary(project, review, payload, len(verified_cases)),
        limitations=_limitations(payload, project, review, verified_cases, ranked),
    )


def _candidate_response(
    ranked: RankedCandidateCase,
    payload: FaultDiagnosisRequest,
    project: Project,
    review: ReviewRun | None,
) -> CandidateCause:
    # The concrete type is established by rank_candidate_cases; keeping the
    # mapping here makes the API layer free of diagnosis logic.
    item = ranked
    case = item.case
    supporting = [
        DiagnosisEvidenceItem(
            source=DiagnosisEvidenceSource.VERIFIED_FAULT_CASE,
            description=(
                f"已核验故障案例 {case.case_id} 与症状匹配；根因文本仅作为案例记录引用。"
            ),
            references=(case.case_id,),
        )
    ]
    observed_matches = item.observed_match_tokens
    waveform_matches = item.waveform_match_tokens
    if observed_matches:
        supporting.append(
            DiagnosisEvidenceItem(
                source=DiagnosisEvidenceSource.USER_INPUT,
                description=(
                    "输入 observed_features 与案例文本存在 token overlap："
                    + ", ".join(observed_matches)
                ),
            )
        )
    if waveform_matches:
        supporting.append(
            DiagnosisEvidenceItem(
                source=DiagnosisEvidenceSource.WAVEFORM,
                description=(
                    "输入 waveform_features 与案例文本存在 token overlap："
                    + ", ".join(waveform_matches)
                ),
            )
        )
    parameter_names = project_parameter_names(project)
    if parameter_names:
        supporting.append(
            DiagnosisEvidenceItem(
                source=DiagnosisEvidenceSource.PROJECT,
                description=(
                    "项目结构化参数已作为诊断上下文提供；"
                    "本阶段不从参数文本自动推导根因。"
                ),
                references=parameter_names,
            )
        )
    if review is not None:
        report_eligible_rule_ids = tuple(
            finding.rule_id for finding in review.findings if finding.report_eligible
        )
        supporting.append(
            DiagnosisEvidenceItem(
                source=DiagnosisEvidenceSource.DESIGN_REVIEW,
                description=(
                    f"项目 {project.id} 有最新 Review {review.id}；"
                    "本阶段不从规则 Finding 自动推导根因。"
                ),
                references=(review.id, *report_eligible_rule_ids),
            )
        )

    missing: list[str] = []
    if not payload.observed_features:
        missing.append("未提供 observed_features。")
    if not payload.waveform_features:
        missing.append("未提供 waveform_features。")
    if review is None:
        missing.append("该项目尚未执行 Design Review。")
    if not project_parameter_names(project):
        missing.append("未提供结构化项目设计参数。")
    if not case.waveform_references:
        missing.append("该已核验案例没有 before/after waveform 引用。")
    if not observed_matches and not waveform_matches:
        missing.append("输入特征与该案例记录没有 token overlap。")

    contradicting = tuple(
        DiagnosisEvidenceItem(
            source=DiagnosisEvidenceSource.USER_INPUT,
            description=(
                "调用方标记的 contradicting_features（系统未独立验证）：" + feature
            ),
        )
        for feature in payload.contradicting_features
    )

    return CandidateCause(
        source_case_id=case.case_id,
        cause=case.root_cause,
        confidence=item.confidence,
        supporting_evidence=tuple(supporting),
        contradicting_evidence=contradicting,
        missing_information=tuple(missing),
        next_measurement=tuple(case.verification_steps),
        recommended_action=tuple(case.fix),
    )


def _evidence_summary(
    project: Project,
    review: ReviewRun | None,
    payload: FaultDiagnosisRequest,
    verified_case_count: int,
) -> DiagnosisEvidenceSummary:
    return DiagnosisEvidenceSummary(
        project_id=project.id,
        project_parameter_names=project_parameter_names(project),
        review_id=review.id if review is not None else None,
        report_eligible_rule_ids=(
            tuple(
                finding.rule_id
                for finding in review.findings
                if finding.report_eligible
            )
            if review is not None
            else ()
        ),
        waveform_feature_names=payload.waveform_features,
        verified_case_count=verified_case_count,
    )


def project_parameter_names(project: Project) -> tuple[str, ...]:
    names: list[str] = []
    for specifications in (
        PROJECT_QUANTITIES,
        PRIMARY_SWITCH_QUANTITIES,
        RESONANT_CAPACITOR_QUANTITIES,
        CONTROLLER_QUANTITIES,
    ):
        names.extend(
            name
            for name, specification in specifications.items()
            if getattr(project, specification.model_attribute) is not None
        )
    return tuple(names)


def _limitations(
    payload: FaultDiagnosisRequest,
    project: Project,
    review: ReviewRun | None,
    verified_cases: Sequence[FaultCase],
    ranked: Sequence[RankedCandidateCase],
) -> tuple[str, ...]:
    limitations = [
        "候选根因只来自 engineer_verified=true 的 FaultCase，不会生成新的根因。",
        "confidence 是确定性的 token overlap 检索分数，不是概率、安全结论或工程裕量。",
        "本阶段不使用 LLM/RAG，也不从 LLC 物理模型推导根因。",
        "每个候选的验证步骤和修复措施均来自案例记录，必须由合格工程师复核。",
    ]
    if review is None:
        limitations.append("当前项目没有可用的最新 Design Review。")
    if not project_parameter_names(project):
        limitations.append("当前项目没有可用的结构化设计参数。")
    if not payload.waveform_features:
        limitations.append("当前请求没有提供 waveform_features。")
    if not verified_cases:
        limitations.append("没有与当前症状匹配的已核验 FaultCase。")
    if len(ranked) < 3:
        limitations.append("可用证据不足，候选数量少于工作流要求的 Top 3。")
    return tuple(limitations)
