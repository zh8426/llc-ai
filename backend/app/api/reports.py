from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.projects import require_project
from app.api.reviews import require_review
from app.database import get_session
from app.services.reports import ReportSnapshotMissingError, render_review_run
from app.services.reviews import get_latest_review

router = APIRouter(prefix="/projects", tags=["reports"])
history_router = APIRouter(prefix="/reviews", tags=["reports"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get(
    "/{project_id}/report",
    response_class=HTMLResponse,
    summary="Render the latest Design Review as HTML",
)
def get_project_report(project_id: str, session: SessionDependency) -> HTMLResponse:
    require_project(session, project_id)
    review = get_latest_review(session, project_id)
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No review has been run for this project",
        )
    try:
        content = render_review_run(review)
    except ReportSnapshotMissingError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    return HTMLResponse(content=content)


@history_router.get(
    "/{review_id}/report",
    response_class=HTMLResponse,
    summary="Render a historical Design Review as HTML",
)
def get_historical_review_report(
    review_id: str, session: SessionDependency
) -> HTMLResponse:
    review = require_review(session, review_id)
    try:
        content = render_review_run(review)
    except ReportSnapshotMissingError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    return HTMLResponse(content=content)
