import datetime as dt

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from core.auth import create_user
from core.models import (
    CardioEntry, ChatMessage, Conversation, Exercise, Food, FoodLog, Profile,
    WorkoutSession, WorkoutSet,
)

TODAY = dt.date(2026, 11, 12)


@pytest.fixture
def user(session):
    return create_user(session, "lifter", "supersecret")


@pytest.fixture
def bench(session):
    ex = Exercise(name="Barbell Bench Press", primary_muscle="chest",
                  secondary_muscles=["triceps", "front_delts"], equipment="barbell")
    session.add(ex)
    session.flush()
    return ex


def count(session, model):
    return session.scalar(select(func.count()).select_from(model))


def test_workout_sets_come_back_in_order(session, user, bench):
    workout = WorkoutSession(user=user, date=TODAY, name="Push Day")
    # Added out of order on purpose.
    workout.sets = [
        WorkoutSet(exercise=bench, exercise_order=0, set_index=2, reps=4, weight_lb=155),
        WorkoutSet(exercise=bench, exercise_order=0, set_index=0, reps=8, weight_lb=135),
        WorkoutSet(exercise=bench, exercise_order=0, set_index=1, reps=6, weight_lb=145),
    ]
    session.add(workout)
    session.commit()
    session.expire_all()

    loaded = session.get(WorkoutSession, workout.id)
    assert [(s.reps, s.weight_lb) for s in loaded.sets] == [(8, 135), (6, 145), (4, 155)]


def test_food_log_keeps_its_numbers_when_food_is_deleted(session, user):
    egg = Food(name="Egg", source="custom", kcal_100g=143, protein_100g=12.6)
    session.add(egg)
    session.flush()
    log = FoodLog(user=user, date=TODAY, meal="breakfast", food=egg, name="Egg",
                  quantity_g=100, kcal=143, protein_g=12.6)
    session.add(log)
    session.commit()

    session.delete(egg)
    session.commit()
    session.expire_all()

    kept = session.get(FoodLog, log.id)
    assert kept.food_id is None
    assert (kept.name, kept.kcal, kept.protein_g) == ("Egg", 143, 12.6)


def test_exercise_with_logged_sets_cannot_be_deleted(session, user, bench):
    session.add(WorkoutSession(user=user, date=TODAY,
                               sets=[WorkoutSet(exercise=bench, reps=5, weight_lb=185)]))
    session.commit()
    with pytest.raises(IntegrityError):
        session.execute(Exercise.__table__.delete().where(Exercise.id == bench.id))


def test_deleting_user_removes_all_their_data(session, user, bench):
    workout = WorkoutSession(user=user, date=TODAY,
                             sets=[WorkoutSet(exercise=bench, reps=5, weight_lb=185)])
    session.add_all([
        workout,
        CardioEntry(user=user, date=TODAY, activity="cycle", duration_min=15, session=workout),
        FoodLog(user=user, date=TODAY, meal="lunch", name="Rice", quantity_g=200, kcal=260),
        Food(name="My shake", source="custom", kcal_100g=90, user=user),
        Exercise(name="My curl", primary_muscle="biceps", equipment="cable", user=user),
        Conversation(user=user, messages=[ChatMessage(role="user", content={"text": "hi"})]),
    ])
    session.commit()

    session.delete(user)
    session.commit()

    for model in (Profile, WorkoutSession, WorkoutSet, CardioEntry, FoodLog, Food,
                  Conversation, ChatMessage):
        assert count(session, model) == 0, model.__name__
    # Built-in exercises are shared and must survive.
    assert session.scalars(select(Exercise.name)).all() == ["Barbell Bench Press"]


@pytest.mark.parametrize("make", [
    lambda: FoodLog(meal="brunch"),
    lambda: Exercise(primary_muscle="neck"),
    lambda: Exercise(secondary_muscles=["chest", "wings"]),
    lambda: Exercise(equipment="spaceship"),
    lambda: CardioEntry(activity="teleport"),
    lambda: Profile(goal="get huge"),
    lambda: WorkoutSet(rpe=11),
    lambda: WorkoutSet(weight_lb=-5),
    lambda: Food(kcal_100g=-1),
])
def test_invalid_values_are_rejected(make):
    with pytest.raises(ValueError):
        make()
