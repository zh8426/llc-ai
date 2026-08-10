from sqlalchemy import MetaData

from app.models import Base


def test_sqlalchemy_declarative_base_is_available_without_domain_models() -> None:
    assert isinstance(Base.metadata, MetaData)
    assert list(Base.metadata.tables) == []

