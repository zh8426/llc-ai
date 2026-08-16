from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database import create_database_engine
from app.models import (
    Base,
    DatasheetDocument,
    DatasheetParameter,
    Project,
    ReviewCalculationSnapshot,
    ReviewFinding,
    ReviewProjectSnapshot,
    ReviewRun,
)


def test_sqlite_engine_enables_foreign_keys() -> None:
    engine = create_database_engine("sqlite://")
    try:
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
    finally:
        engine.dispose()


def test_sqlite_project_delete_cascades_review_tree() -> None:
    engine = create_database_engine("sqlite://")
    Base.metadata.create_all(engine)
    project_id = "project-cascade-test"
    review_id = "review-cascade-test"

    try:
        with Session(engine) as session:
            session.add(
                Project(
                    id=project_id,
                    name="Cascade test project",
                    topology="Half-Bridge LLC",
                )
            )
            session.flush()
            session.add_all(
                [
                    ReviewRun(
                        id=review_id,
                        project_id=project_id,
                        pass_count=1,
                        info_count=0,
                        warning_count=0,
                        critical_count=0,
                        insufficient_data_count=0,
                    ),
                    ReviewFinding(
                        id="finding-cascade-test",
                        review_id=review_id,
                        position=1,
                        rule_id="TEST-R001",
                        category="Test",
                        severity="PASS",
                        title="Cascade test finding",
                        description="Synthetic row used to verify database cascade behavior.",
                        evidence=[{"source": "test"}],
                        calculated_values={},
                        missing_information=[],
                        recommended_action=[],
                        requires_engineer_confirmation=False,
                        report_eligible=True,
                    ),
                    ReviewProjectSnapshot(
                        review_id=review_id,
                        project_data={"name": "Cascade test project"},
                    ),
                    ReviewCalculationSnapshot(
                        review_id=review_id,
                        calculated_at=datetime.now(UTC),
                        engine_version="test",
                        calculations=[],
                        missing_information=[],
                        errors={},
                    ),
                ]
            )
            session.commit()

            session.execute(delete(Project).where(Project.id == project_id))
            session.commit()

            for model in (
                ReviewRun,
                ReviewFinding,
                ReviewProjectSnapshot,
                ReviewCalculationSnapshot,
            ):
                assert session.scalar(select(func.count()).select_from(model)) == 0
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_sqlite_datasheet_delete_cascades_parameters() -> None:
    engine = create_database_engine("sqlite://")
    Base.metadata.create_all(engine)
    document_id = "datasheet-cascade-test"

    try:
        with Session(engine) as session:
            session.add(
                DatasheetDocument(
                    id=document_id,
                    filename="cascade.pdf",
                    content_type="application/pdf",
                    parser_status="NEEDS_HUMAN_REVIEW",
                    page_count=1,
                )
            )
            session.flush()
            session.add(
                DatasheetParameter(
                    id="parameter-cascade-test",
                    document_id=document_id,
                    position=0,
                    parameter_name="VDS",
                    value_numeric=650,
                    unit="V",
                    value_type="maximum",
                    test_condition={"source_line": "VDS 650 V maximum"},
                    source_page=1,
                    confidence=0.8,
                    human_verified=False,
                )
            )
            session.commit()

            session.execute(delete(DatasheetDocument).where(DatasheetDocument.id == document_id))
            session.commit()

            assert session.scalar(select(func.count()).select_from(DatasheetParameter)) == 0
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
