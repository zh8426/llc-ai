from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.database import get_session
from app.schemas.diagnosis import FaultDiagnosisRequest, FaultDiagnosisResponse
from app.services.diagnosis import diagnose_fault

router = APIRouter(prefix="/fault-diagnoses", tags=["fault-diagnosis"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.post(
    "",
    response_model=FaultDiagnosisResponse,
    status_code=status.HTTP_200_OK,
    summary="Run deterministic fault diagnosis orchestration",
)
def post_fault_diagnosis(
    payload: FaultDiagnosisRequest, session: SessionDependency
) -> FaultDiagnosisResponse:
    try:
        return diagnose_fault(session, payload)
    except LookupError as error:
        raise APIError(
            status.HTTP_404_NOT_FOUND,
            "PROJECT_NOT_FOUND",
            "项目不存在。",
            details={"project_id": payload.project_id},
        ) from error
