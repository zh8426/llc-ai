from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.models import Base
from app.models.project import Project

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BASELINE_REVISION = "0001_phase0_4_baseline"
HEAD_REVISION = "0004_fault_cases"
APPLICATION_TABLES = {
    "datasheet_documents",
    "datasheet_parameters",
    "fault_cases",
    "projects",
    "review_calculation_snapshots",
    "review_runs",
    "review_findings",
    "review_project_snapshots",
}


def migration_config(database_url: str) -> Config:
    config = Config(str(REPOSITORY_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_baseline_migration_builds_schema_matching_models(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    database_url = f"sqlite:///{(tmp_path / 'new.sqlite3').as_posix()}"
    config = migration_config(database_url)

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == {*APPLICATION_TABLES, "alembic_version"}

    with engine.connect() as connection:
        migration_context = MigrationContext.configure(connection)
        assert migration_context.get_current_revision() == HEAD_REVISION
        assert compare_metadata(migration_context, Base.metadata) == []

    command.downgrade(config, "base")
    assert not APPLICATION_TABLES.intersection(inspect(engine).get_table_names())
    engine.dispose()


def test_existing_phase0_4_database_can_be_stamped_without_data_loss(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    database_url = f"sqlite:///{(tmp_path / 'existing.sqlite3').as_posix()}"
    config = migration_config(database_url)
    command.upgrade(config, BASELINE_REVISION)
    engine = create_engine(database_url)

    project_id = "existing-phase0-4-project"
    with Session(engine) as session:
        session.add(Project(id=project_id, name="Existing Phase 0-4 project"))
        session.commit()

    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE alembic_version")

    command.stamp(config, BASELINE_REVISION)
    command.upgrade(config, "head")

    with engine.connect() as connection:
        migration_context = MigrationContext.configure(connection)
        assert migration_context.get_current_revision() == HEAD_REVISION
    with Session(engine) as session:
        assert session.scalar(select(Project.name).where(Project.id == project_id)) == (
            "Existing Phase 0-4 project"
        )

    engine.dispose()
