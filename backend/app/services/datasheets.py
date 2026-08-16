from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.datasheet.parser import DatasheetCandidate
from app.models.datasheet import DatasheetDocument, DatasheetParameter
from app.schemas.datasheet import (
    DatasheetParameterUpdate,
    DatasheetParserStatus,
)


def create_datasheet_document(
    session: Session,
    *,
    filename: str,
    content_type: str,
    manufacturer: str | None,
    part_number: str | None,
    page_count: int,
    candidates: Sequence[DatasheetCandidate],
) -> DatasheetDocument:
    document = DatasheetDocument(
        filename=filename,
        content_type=content_type,
        manufacturer=manufacturer,
        part_number=part_number,
        parser_status=(
            DatasheetParserStatus.NEEDS_HUMAN_REVIEW
            if candidates
            else DatasheetParserStatus.NO_SUPPORTED_PARAMETERS
        ),
        parser_message=None,
        page_count=page_count,
    )
    session.add(document)
    session.flush()
    for position, candidate in enumerate(candidates):
        numeric_value = candidate.value if isinstance(candidate.value, (int, float)) else None
        text_value = candidate.value if isinstance(candidate.value, str) else None
        document.parameters.append(
            DatasheetParameter(
                document_id=document.id,
                position=position,
                parameter_name=candidate.parameter_name.value,
                value_numeric=numeric_value,
                value_text=text_value,
                unit=candidate.unit,
                value_type=candidate.value_type.value,
                test_condition=candidate.test_condition,
                source_page=candidate.source_page,
                confidence=candidate.confidence,
                human_verified=False,
            )
        )
    session.commit()
    return get_datasheet_document(session, document.id)  # type: ignore[return-value]


def list_datasheet_documents(session: Session) -> list[DatasheetDocument]:
    return list(
        session.scalars(
            select(DatasheetDocument)
            .options(selectinload(DatasheetDocument.parameters))
            .order_by(DatasheetDocument.created_at.desc())
        ).all()
    )


def get_datasheet_document(session: Session, document_id: str) -> DatasheetDocument | None:
    return session.scalar(
        select(DatasheetDocument)
        .options(selectinload(DatasheetDocument.parameters))
        .where(DatasheetDocument.id == document_id)
    )


def get_datasheet_parameter(
    session: Session, document_id: str, parameter_id: str
) -> DatasheetParameter | None:
    return session.scalar(
        select(DatasheetParameter).where(
            DatasheetParameter.document_id == document_id,
            DatasheetParameter.id == parameter_id,
        )
    )


def update_datasheet_parameter(
    session: Session,
    document: DatasheetDocument,
    parameter: DatasheetParameter,
    payload: DatasheetParameterUpdate,
) -> DatasheetDocument:
    if payload.value is not None:
        if isinstance(payload.value, str):
            parameter.value_text = payload.value
            parameter.value_numeric = None
        else:
            parameter.value_numeric = payload.value
            parameter.value_text = None
    if payload.unit is not None:
        parameter.unit = payload.unit
    if payload.value_type is not None:
        parameter.value_type = payload.value_type.value
    if payload.test_condition is not None:
        parameter.test_condition = payload.test_condition
    if payload.source_page is not None:
        parameter.source_page = payload.source_page
    if payload.confidence is not None:
        parameter.confidence = payload.confidence
    if payload.human_verified is not None:
        parameter.human_verified = payload.human_verified

    parameters = list(document.parameters)
    document.parser_status = (
        DatasheetParserStatus.VERIFIED
        if parameters and all(item.human_verified for item in parameters)
        else DatasheetParserStatus.NEEDS_HUMAN_REVIEW
    )
    session.commit()
    return get_datasheet_document(session, document.id)  # type: ignore[return-value]
