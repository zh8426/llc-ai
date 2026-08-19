from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.database import get_session
from app.engine.exceptions import EngineeringCalculationError
from app.models.project import Project
from app.schemas.project import (
    ProjectCalculationResponse,
    ProjectCreate,
    ProjectGainCurveRequest,
    ProjectGainCurveResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.calculations import (
    ProjectGainCurveMissingDataError,
    calculate_project,
    calculate_project_gain_curve,
)
from app.services.projects import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    project_to_response,
    update_project,
)

router = APIRouter(prefix="/projects", tags=["projects"])
SessionDependency = Annotated[Session, Depends(get_session)]


def require_project(session: Session, project_id: str) -> Project:
    project = get_project(session, project_id)
    if project is None:
        raise APIError(
            status.HTTP_404_NOT_FOUND,
            "PROJECT_NOT_FOUND",
            "项目不存在。",
            details={"project_id": project_id},
        )
    return project


@router.get("", response_model=ProjectListResponse)
def get_projects(session: SessionDependency) -> ProjectListResponse:
    return ProjectListResponse(
        projects=tuple(
            project_to_response(project) for project in list_projects(session)
        )
    )


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_project(
    payload: ProjectCreate, session: SessionDependency
) -> ProjectResponse:
    try:
        project = create_project(session, payload)
    except EngineeringCalculationError as error:
        session.rollback()
        raise APIError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "INVALID_ENGINEERING_UNIT",
            "工程参数单位或数值无效。",
            details={"reason": str(error)},
        ) from error
    return project_to_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project_by_id(
    project_id: str, session: SessionDependency
) -> ProjectResponse:
    return project_to_response(require_project(session, project_id))


@router.patch("/{project_id}", response_model=ProjectResponse)
def patch_project(
    project_id: str,
    payload: ProjectUpdate,
    session: SessionDependency,
) -> ProjectResponse:
    project = require_project(session, project_id)
    try:
        project = update_project(session, project, payload)
    except EngineeringCalculationError as error:
        session.rollback()
        raise APIError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "INVALID_ENGINEERING_UNIT",
            "工程参数单位或数值无效。",
            details={"reason": str(error)},
        ) from error
    except ValueError as error:
        session.rollback()
        raise APIError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "INVALID_REQUEST",
            "请求参数无效。",
            details={"reason": str(error)},
        ) from error
    return project_to_response(project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project and its dependent review history",
)
def delete_project_by_id(
    project_id: str, session: SessionDependency
) -> Response:
    project = require_project(session, project_id)
    delete_project(session, project)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{project_id}/calculate",
    response_model=ProjectCalculationResponse,
)
def post_project_calculation(
    project_id: str, session: SessionDependency
) -> ProjectCalculationResponse:
    return calculate_project(require_project(session, project_id))


@router.post(
    "/{project_id}/gain-curve",
    response_model=ProjectGainCurveResponse,
    summary="Generate a deterministic FHA gain curve for a project",
)
def post_project_gain_curve(
    project_id: str,
    payload: ProjectGainCurveRequest,
    session: SessionDependency,
) -> ProjectGainCurveResponse:
    try:
        return calculate_project_gain_curve(
            require_project(session, project_id), point_count=payload.point_count
        )
    except ProjectGainCurveMissingDataError as error:
        raise APIError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "MISSING_REQUIRED_DATA",
            "生成增益曲线所需的项目参数不完整。",
            details={"missing_information": error.missing_information},
        ) from error
    except EngineeringCalculationError as error:
        raise APIError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "INVALID_ENGINEERING_UNIT",
            "增益曲线输入的工程单位或数值无效。",
            details={"reason": str(error)},
        ) from error
