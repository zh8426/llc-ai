from fastapi import APIRouter, status

from app.schemas.health import HealthResponse

router = APIRouter(tags=["system"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check Backend availability",
)
def get_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="llc-engineering-assistant-backend",
        version="0.1.0",
    )

