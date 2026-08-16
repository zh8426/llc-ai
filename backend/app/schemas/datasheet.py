from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DatasheetParserStatus(StrEnum):
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"
    VERIFIED = "VERIFIED"
    NO_SUPPORTED_PARAMETERS = "NO_SUPPORTED_PARAMETERS"


class DatasheetParameterName(StrEnum):
    VDS = "VDS"
    ID = "ID"
    RDS_ON = "Rds(on)"
    QG = "Qg"
    COSS = "Coss"
    EOSS = "Eoss"
    RTHJC = "RthJC"
    TJ_MAX = "Tj Max"
    PACKAGE = "Package"


class DatasheetValueType(StrEnum):
    MINIMUM = "minimum"
    TYPICAL = "typical"
    MAXIMUM = "maximum"
    UNKNOWN = "unknown"


class DatasheetParameterResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    parameter_name: DatasheetParameterName
    value: float | str
    unit: str
    value_type: DatasheetValueType
    test_condition: dict[str, str]
    source_page: int | None
    confidence: float = Field(ge=0, le=1)
    human_verified: bool


class DatasheetDocumentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    filename: str
    content_type: str
    manufacturer: str | None
    part_number: str | None
    parser_status: DatasheetParserStatus
    parser_message: str | None
    page_count: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime
    parameters: tuple[DatasheetParameterResponse, ...]


class DatasheetListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    datasheets: tuple[DatasheetDocumentResponse, ...]


class DatasheetParameterUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float | str | None = None
    unit: str | None = Field(default=None, min_length=1)
    value_type: DatasheetValueType | None = None
    test_condition: dict[str, str] | None = None
    source_page: int | None = Field(default=None, ge=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    human_verified: bool | None = None
