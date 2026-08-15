from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.projects import require_project
from app.database import get_session
from app.models.review import ReviewRun
from app.schemas.project import ProjectReviewHistoryResponse, ProjectReviewResponse
from app.services.reviews import (
    get_latest_review,
    get_review,
    list_reviews,
    review_to_history_item,
    review_to_response,
    run_and_store_review,
)

router = APIRouter(prefix="/projects", tags=["reviews"])
history_router = APIRouter(prefix="/reviews", tags=["reviews"])
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


@router.get("/{project_id}/reviews", response_model=ProjectReviewHistoryResponse)
def get_project_review_history(
    project_id: str, session: SessionDependency
) -> ProjectReviewHistoryResponse:
    require_project(session, project_id)
    return ProjectReviewHistoryResponse(
        project_id=project_id,
        reviews=tuple(
            review_to_history_item(review)
            for review in list_reviews(session, project_id)
        ),
    )


def require_review(session: Session, review_id: str) -> ReviewRun:
    try:
        return get_review(session, review_id)
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        ) from error


@history_router.get("/{review_id}", response_model=ProjectReviewResponse)
def get_historical_review(
    review_id: str, session: SessionDependency
) -> ProjectReviewResponse:
    return review_to_response(require_review(session, review_id))
