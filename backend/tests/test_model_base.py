from sqlalchemy import MetaData

from app.models import Base


def test_sqlalchemy_metadata_contains_persistence_models() -> None:
    assert isinstance(Base.metadata, MetaData)
    assert set(Base.metadata.tables) == {
        "datasheet_documents",
        "datasheet_parameters",
        "fault_cases",
        "projects",
        "review_calculation_snapshots",
        "review_runs",
        "review_findings",
        "review_project_snapshots",
    }
