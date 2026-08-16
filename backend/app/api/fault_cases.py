from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.database import get_session
from app.engine.exceptions import EngineeringCalculationError
from app.models.fault_case import FaultCase
from app.schemas.engineering import EngineeringQuantity
from app.schemas.fault_case import (
    FaultCaseCreate,
    FaultCaseListResponse,
    FaultCaseResponse,
    FaultCaseUpdate,
    FaultSymptom,
)
from app.services.fault_cases import (
    create_fault_case,
    get_fault_case,
    search_fault_cases,
    update_fault_case,
)

router = APIRouter(prefix="/fault-cases", tags=["fault-cases"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.post(
    "",
    response_model=FaultCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create one structured fault case",
)
def post_fault_case(
    payload: FaultCaseCreate, session: SessionDependency
) -> FaultCaseResponse:
    try:
        case = create_fault_case(session, payload)
    except EngineeringCalculationError as error:
        session.rollback()
        raise APIError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "INVALID_ENGINEERING_UNIT",
            "故障案例工况单位或数值无效。",
            details={"reason": str(error)},
        ) from error
    return _case_response(case)


@router.get("", response_model=FaultCaseListResponse)
def get_fault_cases(
    session: SessionDependency,
    query: Annotated[str | None, Query(max_length=500)] = None,
    symptom: FaultSymptom | None = None,
    engineer_verified: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> FaultCaseListResponse:
    results = search_fault_cases(
        session,
        query=query,
        symptom=symptom,
        engineer_verified=engineer_verified,
        limit=limit,
    )
    return FaultCaseListResponse(
        cases=tuple(_case_response(case, score) for case, score in results)
    )


@router.get("/{case_id}", response_model=FaultCaseResponse)
def get_fault_case_by_id(
    case_id: str, session: SessionDependency
) -> FaultCaseResponse:
    return _case_response(_require_case(session, case_id))


@router.patch("/{case_id}", response_model=FaultCaseResponse)
def patch_fault_case(
    case_id: str,
    payload: FaultCaseUpdate,
    session: SessionDependency,
) -> FaultCaseResponse:
    case = _require_case(session, case_id)
    try:
        updated = update_fault_case(session, case, payload)
    except EngineeringCalculationError as error:
        session.rollback()
        raise APIError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "INVALID_ENGINEERING_UNIT",
            "故障案例工况单位或数值无效。",
            details={"reason": str(error)},
        ) from error
    return _case_response(updated)


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fault_case(case_id: str, session: SessionDependency) -> Response:
    case = _require_case(session, case_id)
    session.delete(case)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _require_case(session: Session, case_id: str) -> FaultCase:
    case = get_fault_case(session, case_id)
    if case is None:
        raise APIError(
            status.HTTP_404_NOT_FOUND,
            "FAULT_CASE_NOT_FOUND",
            "故障案例不存在。",
            details={"case_id": case_id},
        )
    return case


def _case_response(case: FaultCase, similarity_score: float | None = None) -> FaultCaseResponse:
    return FaultCaseResponse(
        case_id=case.case_id,
        topology=cast(Literal["Half-Bridge LLC"], case.topology),
        power=_from_storage(case.power_w, "W"),
        vin=_from_storage(case.vin_v, "V"),
        vout=_from_storage(case.vout_v, "V"),
        load=case.load_description,
        symptom=FaultSymptom(case.symptom),
        observed_features=tuple(case.observed_features),
        root_cause=case.root_cause,
        verification_steps=tuple(case.verification_steps),
        fix=tuple(case.fix),
        waveform_before=case.waveform_before,
        waveform_after=case.waveform_after,
        engineer_verified=case.engineer_verified,
        production_evidence_eligible=case.engineer_verified,
        verification_notes=case.verification_notes,
        similarity_score=similarity_score,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


def _from_storage(value: float | None, unit: str) -> EngineeringQuantity | None:
    if value is None:
        return None
    return EngineeringQuantity(value=value, unit=unit)
