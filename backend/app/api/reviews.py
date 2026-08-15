from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.projects import require_project
from app.database import get_session
from app.schemas.project import ProjectReviewResponse
from app.services.reviews import (
    get_latest_review,
    review_to_response,
    run_and_store_review,
)

router = APIRouter(prefix="/projects", tags=["reviews"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.post(
    "/{project_id}/review",
    response_model=ProjectReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_project_review(
    project_id: str, session: SessionDependency
) -> ProjectReviewResponse:
    project = require_project(session, project_id)
    return review_to_response(run_and_store_review(session, project))


@router.get("/{project_id}/review", response_model=ProjectReviewResponse)
def get_project_review(
    project_id: str, session: SessionDependency
) -> ProjectReviewResponse:
    require_project(session, project_id)
    review = get_latest_review(session, project_id)
    if review is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No review has been run for this project",
        )
    return review_to_response(review)
