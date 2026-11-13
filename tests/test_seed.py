from collections import Counter

from sqlalchemy import func, select

from core import constants as C
from core.models import Exercise
from core.seed import load_exercise_library, seed_exercises


def test_exercise_library_is_valid():
    library = load_exercise_library()
    assert len(library) >= 90

    dupes = [name for name, n in Counter(e["name"] for e in library).items() if n > 1]
    assert not dupes, f"duplicate exercises: {dupes}"

    for e in library:
        assert e["primary"] in C.MUSCLES, e["name"]
        assert e["equipment"] in C.EQUIPMENT, e["name"]
        assert all(m in C.MUSCLES for m in e["secondary"]), e["name"]
        assert e["primary"] not in e["secondary"], e["name"]

    # Every muscle should have at least one exercise that targets it directly.
    assert {e["primary"] for e in library} == set(C.MUSCLES)


def test_seeding_is_idempotent(session):
    total = len(load_exercise_library())
    assert seed_exercises(session) == total
    session.commit()
    assert seed_exercises(session) == 0
    assert session.scalar(select(func.count()).select_from(Exercise)) == total
