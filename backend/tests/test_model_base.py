from sqlalchemy import MetaData

from app.models import Base


def test_sqlalchemy_metadata_contains_phase_3_persistence_models() -> None:
    assert isinstance(Base.metadata, MetaData)
    assert set(Base.metadata.tables) == {
        "projects",
        "review_runs",
        "review_findings",
        "review_project_snapshots",
    }
