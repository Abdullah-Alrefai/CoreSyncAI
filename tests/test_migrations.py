from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy.orm import Session

from core.db import make_engine, run_migrations
from core.models import Base
from core.seed import seed_exercises


def test_migrations_match_models(tmp_path):
    """Fails if models.py changed without a matching Alembic migration."""
    url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    run_migrations(url)

    engine = make_engine(url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == [], f"models.py and migrations differ - run alembic revision --autogenerate: {diff}"

    # The migrated database accepts the seed data.
    with Session(engine) as session:
        assert seed_exercises(session) > 0
        session.commit()
    engine.dispose()
