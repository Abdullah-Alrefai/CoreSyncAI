"""Profile, daily targets and weigh-ins.

BMR uses the Mifflin-St Jeor formula. Inputs are in lb and inches and are
converted to kg and cm for the formula.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import constants as C
from core.models import BodyMetric, Profile

KG_PER_LB = 0.45359237
CM_PER_IN = 2.54

GOAL_KCAL_ADJUSTMENT = {"cut": -500, "maintain": 0, "bulk": 300}
PROTEIN_G_PER_LB = 1.0
FAT_SHARE = 0.25  # share of calories from fat
MIN_KCAL = {"female": 1200, "male": 1500}

KCAL_PER_G_PROTEIN = 4
KCAL_PER_G_CARBS = 4
KCAL_PER_G_FAT = 9

PROFILE_FIELDS = (
    "sex", "birth_date", "height_in", "activity_level", "goal",
    "calorie_target", "protein_target_g", "carbs_target_g", "fat_target_g",
)


# ---------------------------------------------------------------------------
# Pure calculations
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Targets:
    kcal: int
    protein_g: float
    carbs_g: float
    fat_g: float


@dataclass(frozen=True)
class Plan:
    """Computed numbers for a profile, or the fields still missing."""

    bmr: float | None = None
    tdee: float | None = None
    targets: Targets | None = None
    missing: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing


def age_on(birth_date: dt.date, today: dt.date) -> int:
    had_birthday = (today.month, today.day) >= (birth_date.month, birth_date.day)
    return today.year - birth_date.year - (0 if had_birthday else 1)


def bmr_mifflin(sex: str, weight_lb: float, height_in: float, age: int) -> float:
    if sex not in C.SEXES:
        raise ValueError(f"Invalid sex: {sex!r}")
    kg = weight_lb * KG_PER_LB
    cm = height_in * CM_PER_IN
    return 10 * kg + 6.25 * cm - 5 * age + (5 if sex == "male" else -161)


def tdee(bmr: float, activity_level: str) -> float:
    if activity_level not in C.ACTIVITY_LEVELS:
        raise ValueError(f"Invalid activity level: {activity_level!r}")
    return bmr * C.ACTIVITY_LEVELS[activity_level][1]


def suggested_targets(tdee_kcal: float, goal: str, weight_lb: float, sex: str) -> Targets:
    """Daily targets: goal-adjusted calories, 1 g protein/lb, 25% fat, carbs fill the rest."""
    if goal not in C.GOALS:
        raise ValueError(f"Invalid goal: {goal!r}")
    kcal = round(max(tdee_kcal + GOAL_KCAL_ADJUSTMENT[goal], MIN_KCAL.get(sex, 1200)))
    protein = round(weight_lb * PROTEIN_G_PER_LB)
    fat = round(kcal * FAT_SHARE / KCAL_PER_G_FAT)
    remaining = kcal - protein * KCAL_PER_G_PROTEIN - fat * KCAL_PER_G_FAT
    carbs = max(round(remaining / KCAL_PER_G_CARBS), 0)
    return Targets(kcal=kcal, protein_g=protein, carbs_g=carbs, fat_g=fat)


def weight_change(weights: list[BodyMetric], days: int, today: dt.date) -> float | None:
    """Change from the first to the last weigh-in within the last `days` days.

    `weights` must be sorted oldest first (as list_weights returns them).
    Returns None if there are fewer than two weigh-ins in that window.
    """
    start = today - dt.timedelta(days=days)
    window = [w for w in weights if start <= w.date <= today]
    if len(window) < 2:
        return None
    return window[-1].weight_lb - window[0].weight_lb


def compute_plan(profile: Profile, weight_lb: float | None, today: dt.date) -> Plan:
    checks = {
        "sex": profile.sex,
        "birth date": profile.birth_date,
        "height": profile.height_in,
        "activity level": profile.activity_level,
        "weight": weight_lb,
    }
    missing = [name for name, value in checks.items() if not value]
    if missing:
        return Plan(missing=missing)

    bmr = bmr_mifflin(profile.sex, weight_lb, profile.height_in, age_on(profile.birth_date, today))
    total = tdee(bmr, profile.activity_level)
    targets = suggested_targets(total, profile.goal or "maintain", weight_lb, profile.sex)
    return Plan(bmr=bmr, tdee=total, targets=targets)


# ---------------------------------------------------------------------------
# Database operations (the caller commits, e.g. via core.db.session_scope)
# ---------------------------------------------------------------------------
def get_profile(session: Session, user_id: int) -> Profile:
    """Return the user's profile, creating an empty one if it is missing."""
    profile = session.scalar(select(Profile).where(Profile.user_id == user_id))
    if profile is None:
        profile = Profile(user_id=user_id)
        session.add(profile)
        session.flush()
    return profile


def update_profile(session: Session, user_id: int, **fields) -> Profile:
    unknown = set(fields) - set(PROFILE_FIELDS)
    if unknown:
        raise ValueError(f"Unknown profile fields: {', '.join(sorted(unknown))}")
    profile = get_profile(session, user_id)
    for name, value in fields.items():
        setattr(profile, name, value)  # @validates on the model checks values
    session.flush()
    return profile


def latest_weight(session: Session, user_id: int) -> float | None:
    return session.scalar(
        select(BodyMetric.weight_lb)
        .where(BodyMetric.user_id == user_id)
        .order_by(BodyMetric.date.desc())
        .limit(1)
    )


def apply_suggested_targets(session: Session, user_id: int, today: dt.date | None = None) -> Plan:
    """Save the suggested targets to the profile. Returns the plan (check .ok)."""
    profile = get_profile(session, user_id)
    plan = compute_plan(profile, latest_weight(session, user_id), today or dt.date.today())
    if plan.ok:
        t = plan.targets
        profile.calorie_target = t.kcal
        profile.protein_target_g = t.protein_g
        profile.carbs_target_g = t.carbs_g
        profile.fat_target_g = t.fat_g
        session.flush()
    return plan


def log_weight(
    session: Session, user_id: int, date: dt.date, weight_lb: float,
    body_fat_pct: float | None = None,
) -> BodyMetric:
    """Add a weigh-in, or update that day's entry if one exists."""
    entry = session.scalar(
        select(BodyMetric).where(BodyMetric.user_id == user_id, BodyMetric.date == date)
    )
    if entry is None:
        entry = BodyMetric(user_id=user_id, date=date, weight_lb=weight_lb)
        session.add(entry)
    entry.weight_lb = weight_lb
    entry.body_fat_pct = body_fat_pct
    session.flush()
    return entry


def list_weights(
    session: Session, user_id: int, days: int | None = None, today: dt.date | None = None,
) -> list[BodyMetric]:
    """Weigh-ins, oldest first. With days set, only the last N days."""
    query = select(BodyMetric).where(BodyMetric.user_id == user_id)
    if days is not None:
        start = (today or dt.date.today()) - dt.timedelta(days=days - 1)
        query = query.where(BodyMetric.date >= start)
    return list(session.scalars(query.order_by(BodyMetric.date)))


def delete_weight(session: Session, user_id: int, metric_id: int) -> bool:
    """Delete one of the user's weigh-ins. Returns False if not found."""
    entry = session.scalar(
        select(BodyMetric).where(BodyMetric.id == metric_id, BodyMetric.user_id == user_id)
    )
    if entry is None:
        return False
    session.delete(entry)
    session.flush()
    return True
