from typing import Any

from fastapi.responses import JSONResponse

from app.schemas.errors import APIErrorResponse, ErrorCode


class APIError(Exception):
    """A stable, user-facing API error handled by the application boundary."""

    def __init__(
        self,
        status_code: int,
        code: ErrorCode,
        message: str,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def api_error_response(error: APIError) -> JSONResponse:
    payload = APIErrorResponse(
        code=error.code,
        message=error.message,
        details=error.details,
    )
    return JSONResponse(
        status_code=error.status_code,
        content=payload.model_dump(mode="json"),
    )
