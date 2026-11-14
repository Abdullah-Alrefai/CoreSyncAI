import datetime as dt

import pytest

from core.auth import create_user
from core.models import Profile
from core.services import profile as P

TODAY = dt.date(2026, 6, 15)


@pytest.fixture
def user(session):
    return create_user(session, "tester", "password123")


def _macro_kcal(t: P.Targets) -> float:
    return t.protein_g * 4 + t.carbs_g * 4 + t.fat_g * 9


# --- pure calculations ------------------------------------------------------
def test_age_on_before_and_after_birthday():
    assert P.age_on(dt.date(1996, 6, 15), TODAY) == 30
    assert P.age_on(dt.date(1996, 6, 16), TODAY) == 29


def test_bmr_male_known_value():
    assert P.bmr_mifflin("male", 180, 70, 30) == pytest.approx(1782.7, abs=0.5)


def test_bmr_female_is_166_lower_than_male():
    male = P.bmr_mifflin("male", 140, 64, 25)
    female = P.bmr_mifflin("female", 140, 64, 25)
    assert male - female == pytest.approx(166)


def test_tdee_uses_activity_multiplier():
    assert P.tdee(1782.7, "moderate") == pytest.approx(2763.2, abs=0.5)


@pytest.mark.parametrize("goal,adjust", [("cut", -500), ("maintain", 0), ("bulk", 300)])
def test_suggested_targets_per_goal(goal, adjust):
    t = P.suggested_targets(2763, goal, 180, "male")
    assert t.kcal == 2763 + adjust
    assert t.protein_g == 180
    assert t.fat_g == round(t.kcal * 0.25 / 9)
    assert _macro_kcal(t) == pytest.approx(t.kcal, abs=10)


def test_suggested_targets_respect_safety_floor():
    assert P.suggested_targets(1400, "cut", 120, "female").kcal == 1200
    assert P.suggested_targets(1600, "cut", 150, "male").kcal == 1500


def test_carbs_never_negative():
    assert P.suggested_targets(1200, "maintain", 400, "female").carbs_g == 0


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        P.bmr_mifflin("other", 180, 70, 30)
    with pytest.raises(ValueError):
        P.tdee(1800, "couch")
    with pytest.raises(ValueError):
        P.suggested_targets(2000, "shred", 180, "male")


def test_compute_plan_lists_missing_fields():
    plan = P.compute_plan(Profile(goal="maintain"), None, TODAY)
    assert not plan.ok
    assert plan.targets is None
    assert set(plan.missing) == {"sex", "birth date", "height", "activity level", "weight"}


def test_compute_plan_complete():
    profile = Profile(sex="male", birth_date=dt.date(1996, 1, 1), height_in=70,
                      activity_level="moderate", goal="maintain")
    plan = P.compute_plan(profile, 180, TODAY)
    assert plan.ok
    assert plan.bmr == pytest.approx(1782.7, abs=0.5)
    assert plan.targets.kcal == 2763


def test_weight_change_within_window():
    def bm(days_ago, w):
        return P.BodyMetric(date=TODAY - dt.timedelta(days=days_ago), weight_lb=w)

    weights = [bm(40, 190), bm(6, 184), bm(3, 183), bm(0, 182.5)]
    assert P.weight_change(weights, 7, TODAY) == pytest.approx(-1.5)
    assert P.weight_change(weights, 30, TODAY) == pytest.approx(-1.5)
    assert P.weight_change(weights, 90, TODAY) == pytest.approx(-7.5)
    assert P.weight_change([bm(0, 180)], 7, TODAY) is None
    assert P.weight_change([], 7, TODAY) is None


# --- database operations ----------------------------------------------------
def test_update_profile_and_apply_suggested(session, user):
    P.update_profile(session, user.id, sex="male", birth_date=dt.date(1996, 1, 1),
                     height_in=70, activity_level="moderate", goal="cut")
    assert not P.apply_suggested_targets(session, user.id, TODAY).ok  # no weight yet

    P.log_weight(session, user.id, TODAY, 180)
    plan = P.apply_suggested_targets(session, user.id, TODAY)
    profile = P.get_profile(session, user.id)
    assert plan.ok
    assert profile.calorie_target == 2263
    assert profile.protein_target_g == 180


def test_update_profile_rejects_bad_values(session, user):
    with pytest.raises(ValueError):
        P.update_profile(session, user.id, goal="shred")
    with pytest.raises(ValueError):
        P.update_profile(session, user.id, password_hash="x")


def test_log_weight_same_day_updates(session, user):
    P.log_weight(session, user.id, TODAY, 180)
    P.log_weight(session, user.id, TODAY, 178.5, body_fat_pct=15)
    weights = P.list_weights(session, user.id)
    assert len(weights) == 1
    assert weights[0].weight_lb == 178.5
    assert weights[0].body_fat_pct == 15


def test_latest_weight_and_list_window(session, user):
    assert P.latest_weight(session, user.id) is None
    for days_ago, w in [(40, 185), (10, 182), (0, 180)]:
        P.log_weight(session, user.id, TODAY - dt.timedelta(days=days_ago), w)
    assert P.latest_weight(session, user.id) == 180
    assert [m.weight_lb for m in P.list_weights(session, user.id)] == [185, 182, 180]
    assert [m.weight_lb for m in P.list_weights(session, user.id, days=30, today=TODAY)] == [182, 180]


def test_delete_weight_only_own(session, user):
    other = create_user(session, "someone", "password123")
    mine = P.log_weight(session, user.id, TODAY, 180)
    assert not P.delete_weight(session, other.id, mine.id)
    assert P.delete_weight(session, user.id, mine.id)
    assert P.list_weights(session, user.id) == []
