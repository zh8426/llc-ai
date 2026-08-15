from app.models.review import ReviewRun
from app.reports import render_design_review_report
from app.schemas.project import ProjectResponse
from app.services.reviews import review_to_response


class ReportSnapshotMissingError(RuntimeError):
    """Raised when a legacy review has no immutable project snapshot."""


def render_review_run(review: ReviewRun) -> str:
    if review.project_snapshot is None:
        raise ReportSnapshotMissingError(
            "This review predates report snapshots; run the project review again."
        )
    if review.calculation_snapshot is None:
        raise ReportSnapshotMissingError(
            "This review has no Calculation Snapshot; run the project review again."
        )
    project = ProjectResponse.model_validate(review.project_snapshot.project_data)
    response = review_to_response(review)
    if response.calculation_snapshot is None:
        raise ReportSnapshotMissingError(
            "This review has no Calculation Snapshot; run the project review again."
        )
    return render_design_review_report(
        project,
        response,
        response.calculation_snapshot,
    )
