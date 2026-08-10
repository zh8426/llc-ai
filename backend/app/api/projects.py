from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_session
from app.engine.exceptions import EngineeringCalculationError
from app.models.project import Project
from app.schemas.project import (
    ProjectCalculationResponse,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.calculations import calculate_project
from app.services.projects import (
    create_project,
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
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
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
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
    except (EngineeringCalculationError, ValueError) as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    return project_to_response(project)


@router.post(
    "/{project_id}/calculate",
    response_model=ProjectCalculationResponse,
)
def post_project_calculation(
    project_id: str, session: SessionDependency
) -> ProjectCalculationResponse:
    return calculate_project(require_project(session, project_id))
