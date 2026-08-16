from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.database import get_session
from app.datasheet.limits import MAX_DATASHEET_FILE_BYTES
from app.datasheet.parser import (
    DatasheetExtractionError,
    extract_pdf_pages,
    parse_mosfet_datasheet,
)
from app.models.datasheet import DatasheetDocument, DatasheetParameter
from app.schemas.datasheet import (
    DatasheetDocumentResponse,
    DatasheetListResponse,
    DatasheetParameterName,
    DatasheetParameterResponse,
    DatasheetParameterUpdate,
    DatasheetParserStatus,
    DatasheetValueType,
)
from app.services.datasheets import (
    create_datasheet_document,
    get_datasheet_document,
    get_datasheet_parameter,
    list_datasheet_documents,
    update_datasheet_parameter,
)

router = APIRouter(prefix="/datasheets", tags=["datasheets"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.post(
    "",
    response_model=DatasheetDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and conservatively extract a MOSFET PDF datasheet",
)
async def post_datasheet(
    file: Annotated[UploadFile, File(description="MOSFET PDF datasheet")],
    session: SessionDependency,
    manufacturer: Annotated[str | None, Form()] = None,
    part_number: Annotated[str | None, Form()] = None,
) -> DatasheetDocumentResponse:
    filename = file.filename or "datasheet.pdf"
    if not filename.lower().endswith(".pdf") and file.content_type != "application/pdf":
        raise APIError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "DATASHEET_PDF_INVALID",
            "数据手册必须是 PDF 文件。",
        )
    pdf_bytes = await file.read(MAX_DATASHEET_FILE_BYTES + 1)
    if len(pdf_bytes) > MAX_DATASHEET_FILE_BYTES:
        raise APIError(
            status.HTTP_413_CONTENT_TOO_LARGE,
            "DATASHEET_TOO_LARGE",
            "数据手册 PDF 超过大小限制。",
            details={"limit_bytes": MAX_DATASHEET_FILE_BYTES},
        )
    try:
        pages = extract_pdf_pages(pdf_bytes)
        candidates, identity = parse_mosfet_datasheet(pages)
        document = create_datasheet_document(
            session,
            filename=filename,
            content_type=file.content_type or "application/pdf",
            manufacturer=_first_text(manufacturer, identity["manufacturer"]),
            part_number=_first_text(part_number, identity["part_number"]),
            page_count=len(pages),
            candidates=candidates,
        )
    except DatasheetExtractionError as error:
        session.rollback()
        raise APIError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "DATASHEET_PDF_INVALID",
            "PDF 无法提取可验证的文本。",
            details={"reason": str(error)},
        ) from error
    return _document_response(document)


@router.get("", response_model=DatasheetListResponse)
def get_datasheets(session: SessionDependency) -> DatasheetListResponse:
    return DatasheetListResponse(
        datasheets=tuple(
            _document_response(document) for document in list_datasheet_documents(session)
        )
    )


@router.get("/{document_id}", response_model=DatasheetDocumentResponse)
def get_datasheet(
    document_id: str, session: SessionDependency
) -> DatasheetDocumentResponse:
    document = _require_document(session, document_id)
    return _document_response(document)


@router.patch(
    "/{document_id}/parameters/{parameter_id}",
    response_model=DatasheetDocumentResponse,
    summary="Correct or human-verify one extracted datasheet parameter",
)
def patch_datasheet_parameter(
    document_id: str,
    parameter_id: str,
    payload: DatasheetParameterUpdate,
    session: SessionDependency,
) -> DatasheetDocumentResponse:
    document = _require_document(session, document_id)
    parameter = get_datasheet_parameter(session, document_id, parameter_id)
    if parameter is None:
        raise APIError(
            status.HTTP_404_NOT_FOUND,
            "DATASHEET_PARAMETER_NOT_FOUND",
            "数据手册参数不存在。",
            details={"document_id": document_id, "parameter_id": parameter_id},
        )
    updated = update_datasheet_parameter(session, document, parameter, payload)
    return _document_response(updated)


def _require_document(session: Session, document_id: str) -> DatasheetDocument:
    document = get_datasheet_document(session, document_id)
    if document is None:
        raise APIError(
            status.HTTP_404_NOT_FOUND,
            "DATASHEET_NOT_FOUND",
            "数据手册不存在。",
            details={"datasheet_id": document_id},
        )
    return document


def _first_text(primary: str | None, fallback: str | None) -> str | None:
    for value in (primary, fallback):
        if value is not None and value.strip():
            return value.strip()
    return None


def _document_response(document: DatasheetDocument) -> DatasheetDocumentResponse:
    return DatasheetDocumentResponse(
        id=document.id,
        filename=document.filename,
        content_type=document.content_type,
        manufacturer=document.manufacturer,
        part_number=document.part_number,
        parser_status=DatasheetParserStatus(document.parser_status),
        parser_message=document.parser_message,
        page_count=document.page_count,
        created_at=document.created_at,
        updated_at=document.updated_at,
        parameters=tuple(_parameter_response(parameter) for parameter in document.parameters),
    )


def _parameter_response(parameter: DatasheetParameter) -> DatasheetParameterResponse:
    value: float | str = (
        parameter.value_numeric
        if parameter.value_numeric is not None
        else (parameter.value_text or "")
    )
    return DatasheetParameterResponse(
        id=parameter.id,
        parameter_name=DatasheetParameterName(parameter.parameter_name),
        value=value,
        unit=parameter.unit,
        value_type=DatasheetValueType(parameter.value_type),
        test_condition=parameter.test_condition,
        source_page=parameter.source_page,
        confidence=parameter.confidence,
        human_verified=parameter.human_verified,
    )
