import pytest
from sqlalchemy.orm import Session

from core.db import make_engine
from core.models import Base


@pytest.fixture
def engine():
    """A fresh in-memory database per test, with foreign keys enforced."""
    eng = make_engine("sqlite://")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s
