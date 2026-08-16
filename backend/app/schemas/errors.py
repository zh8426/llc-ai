from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ErrorCode = Literal[
    "PROJECT_NOT_FOUND",
    "REVIEW_NOT_FOUND",
    "INVALID_ENGINEERING_UNIT",
    "MISSING_REQUIRED_DATA",
    "WAVEFORM_TOO_LARGE",
    "WAVEFORM_SCHEMA_INVALID",
    "ZVS_INSUFFICIENT_DATA",
    "DATABASE_CONFLICT",
    "INVALID_REQUEST",
    "RESOURCE_NOT_FOUND",
    "METHOD_NOT_ALLOWED",
    "INTERNAL_ERROR",
    "DATASHEET_TOO_LARGE",
    "DATASHEET_PDF_INVALID",
    "DATASHEET_NOT_FOUND",
    "DATASHEET_PARAMETER_NOT_FOUND",
]


class APIErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ErrorCode
    message: str = Field(min_length=1)
    details: Any | None = None
