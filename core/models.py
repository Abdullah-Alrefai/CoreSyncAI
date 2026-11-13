"""Database tables for CoreSync AI.

Units: body and lifting weight in pounds (lb), height in inches, distance in
miles. Food amounts are in grams because nutrition data is published per
100 g; the UI converts to servings/ounces for display.

Changing a table here requires a new Alembic migration:
    .venv\\Scripts\\alembic revision --autogenerate -m "describe change"
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import JSON, ForeignKey, Index, MetaData, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, validates

from core import constants as C

# Predictable constraint names (needed for Alembic changes on SQLite).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_N_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _choice(field: str, value: Any, choices, nullable: bool = False) -> Any:
    if value is None and nullable:
        return value
    if value not in choices:
        raise ValueError(f"Invalid {field}: {value!r}. Expected one of: {', '.join(choices)}")
    return value


def _non_negative(field: str, value: float | None) -> float | None:
    if value is not None and value < 0:
        raise ValueError(f"{field} cannot be negative (got {value})")
    return value


def _user_fk() -> Mapped[int]:
    return mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)


def _created_at() -> Mapped[dt.datetime]:
    return mapped_column(default=utcnow)


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(30), unique=True)  # stored lowercase
    password_hash: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[dt.datetime] = _created_at()

    _owned = {"cascade": "all, delete-orphan", "back_populates": "user"}
    profile: Mapped[Profile] = relationship(uselist=False, **_owned)
    body_metrics: Mapped[list[BodyMetric]] = relationship(**_owned)
    custom_foods: Mapped[list[Food]] = relationship(**_owned)
    food_logs: Mapped[list[FoodLog]] = relationship(**_owned)
    saved_meals: Mapped[list[SavedMeal]] = relationship(**_owned)
    custom_exercises: Mapped[list[Exercise]] = relationship(**_owned)
    workout_templates: Mapped[list[WorkoutTemplate]] = relationship(**_owned)
    workout_sessions: Mapped[list[WorkoutSession]] = relationship(**_owned)
    cardio_entries: Mapped[list[CardioEntry]] = relationship(**_owned)
    conversations: Mapped[list[Conversation]] = relationship(**_owned)
    del _owned


class Profile(Base):
    """Body stats and goals; one per user. Targets are per day."""

    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    sex: Mapped[str | None] = mapped_column(String(10))
    birth_date: Mapped[dt.date | None]
    height_in: Mapped[float | None]
    activity_level: Mapped[str | None] = mapped_column(String(20))
    goal: Mapped[str] = mapped_column(String(20), default="maintain")
    calorie_target: Mapped[int | None]
    protein_target_g: Mapped[float | None]
    carbs_target_g: Mapped[float | None]
    fat_target_g: Mapped[float | None]
    updated_at: Mapped[dt.datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="profile")

    @validates("sex")
    def _v_sex(self, _k, v):
        return _choice("sex", v, C.SEXES, nullable=True)

    @validates("activity_level")
    def _v_activity(self, _k, v):
        return _choice("activity level", v, C.ACTIVITY_LEVELS, nullable=True)

    @validates("goal")
    def _v_goal(self, _k, v):
        return _choice("goal", v, C.GOALS)

    @validates("height_in", "calorie_target", "protein_target_g", "carbs_target_g", "fat_target_g")
    def _v_numbers(self, k, v):
        return _non_negative(k, v)


class BodyMetric(Base):
    """A bodyweight weigh-in (one per day)."""

    __tablename__ = "body_metrics"
    __table_args__ = (UniqueConstraint("user_id", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = _user_fk()
    date: Mapped[dt.date]
    weight_lb: Mapped[float]
    body_fat_pct: Mapped[float | None]
    created_at: Mapped[dt.datetime] = _created_at()

    user: Mapped[User] = relationship(back_populates="body_metrics")

    @validates("weight_lb", "body_fat_pct")
    def _v_numbers(self, k, v):
        return _non_negative(k, v)


# ---------------------------------------------------------------------------
# Nutrition
# ---------------------------------------------------------------------------
class Food(Base):
    """A food in the library. Values are per 100 g.

    Doubles as a cache for USDA / Open Food Facts results. Custom foods have
    created_by_user_id set; database foods have it empty and are shared.
    """

    __tablename__ = "foods"
    __table_args__ = (UniqueConstraint("source", "external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    brand: Mapped[str | None] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(10))
    external_id: Mapped[str | None] = mapped_column(String(64))
    barcode: Mapped[str | None] = mapped_column(String(32), index=True)
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kcal_100g: Mapped[float]
    protein_100g: Mapped[float] = mapped_column(default=0)
    carbs_100g: Mapped[float] = mapped_column(default=0)
    fat_100g: Mapped[float] = mapped_column(default=0)
    fiber_100g: Mapped[float | None]
    sugar_100g: Mapped[float | None]
    sodium_mg_100g: Mapped[float | None]
    # e.g. [{"label": "1 large egg", "grams": 50}, {"label": "1 cup", "grams": 243}]
    servings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[dt.datetime] = _created_at()

    user: Mapped[User | None] = relationship(back_populates="custom_foods")

    @validates("source")
    def _v_source(self, _k, v):
        return _choice("food source", v, C.FOOD_SOURCES)

    @validates("kcal_100g", "protein_100g", "carbs_100g", "fat_100g",
               "fiber_100g", "sugar_100g", "sodium_mg_100g")
    def _v_numbers(self, k, v):
        return _non_negative(k, v)


class FoodLog(Base):
    """One food eaten at one meal.

    Name and macros are copied from the food when logged, so correcting a
    food later never rewrites past days. food_id is cleared if the food is
    deleted; the entry stays.
    """

    __tablename__ = "food_logs"
    __table_args__ = (Index("ix_food_logs_user_id_date", "user_id", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    date: Mapped[dt.date]
    meal: Mapped[str] = mapped_column(String(10))
    food_id: Mapped[int | None] = mapped_column(ForeignKey("foods.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(200))
    quantity_g: Mapped[float]
    serving_label: Mapped[str | None] = mapped_column(String(100))  # e.g. "2 x 1 large egg"
    kcal: Mapped[float]
    protein_g: Mapped[float] = mapped_column(default=0)
    carbs_g: Mapped[float] = mapped_column(default=0)
    fat_g: Mapped[float] = mapped_column(default=0)
    fiber_g: Mapped[float | None]
    sugar_g: Mapped[float | None]
    sodium_mg: Mapped[float | None]
    is_estimate: Mapped[bool] = mapped_column(default=False)  # True for AI estimates
    created_at: Mapped[dt.datetime] = _created_at()

    user: Mapped[User] = relationship(back_populates="food_logs")
    food: Mapped[Food | None] = relationship()

    @validates("meal")
    def _v_meal(self, _k, v):
        return _choice("meal", v, C.MEALS)

    @validates("quantity_g", "kcal", "protein_g", "carbs_g", "fat_g",
               "fiber_g", "sugar_g", "sodium_mg")
    def _v_numbers(self, k, v):
        return _non_negative(k, v)


class SavedMeal(Base):
    """A reusable group of foods, e.g. "My usual breakfast"."""

    __tablename__ = "saved_meals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = _user_fk()
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[dt.datetime] = _created_at()

    user: Mapped[User] = relationship(back_populates="saved_meals")
    items: Mapped[list[SavedMealItem]] = relationship(
        back_populates="saved_meal", cascade="all, delete-orphan",
        order_by=lambda: SavedMealItem.position,
    )


class SavedMealItem(Base):
    __tablename__ = "saved_meal_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    saved_meal_id: Mapped[int] = mapped_column(
        ForeignKey("saved_meals.id", ondelete="CASCADE"), index=True
    )
    food_id: Mapped[int] = mapped_column(ForeignKey("foods.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(default=0)
    quantity_g: Mapped[float]
    serving_label: Mapped[str | None] = mapped_column(String(100))

    saved_meal: Mapped[SavedMeal] = relationship(back_populates="items")
    food: Mapped[Food] = relationship()


# ---------------------------------------------------------------------------
# Workouts
# ---------------------------------------------------------------------------
class Exercise(Base):
    """An exercise in the library. Built-in ones have no created_by_user_id."""

    __tablename__ = "exercises"
    __table_args__ = (UniqueConstraint("name", "created_by_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    primary_muscle: Mapped[str] = mapped_column(String(20))
    secondary_muscles: Mapped[list[str]] = mapped_column(JSON, default=list)
    equipment: Mapped[str] = mapped_column(String(20))
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    user: Mapped[User | None] = relationship(back_populates="custom_exercises")

    @property
    def is_custom(self) -> bool:
        return self.created_by_user_id is not None

    @validates("primary_muscle")
    def _v_primary(self, _k, v):
        return _choice("muscle", v, C.MUSCLES)

    @validates("secondary_muscles")
    def _v_secondary(self, _k, v):
        for m in v or []:
            _choice("muscle", m, C.MUSCLES)
        return list(v or [])

    @validates("equipment")
    def _v_equipment(self, _k, v):
        return _choice("equipment", v, C.EQUIPMENT)


class WorkoutTemplate(Base):
    """A reusable routine, e.g. "Push Day"."""

    __tablename__ = "workout_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = _user_fk()
    name: Mapped[str] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = _created_at()

    user: Mapped[User] = relationship(back_populates="workout_templates")
    exercises: Mapped[list[TemplateExercise]] = relationship(
        back_populates="template", cascade="all, delete-orphan",
        order_by=lambda: TemplateExercise.position,
    )


class TemplateExercise(Base):
    __tablename__ = "template_exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("workout_templates.id", ondelete="CASCADE"), index=True
    )
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(default=0)
    target_sets: Mapped[int | None]
    target_reps: Mapped[str | None] = mapped_column(String(20))  # e.g. "8-12"
    notes: Mapped[str | None] = mapped_column(Text)

    template: Mapped[WorkoutTemplate] = relationship(back_populates="exercises")
    exercise: Mapped[Exercise] = relationship()


class WorkoutSession(Base):
    """One lifting workout on one day."""

    __tablename__ = "workout_sessions"
    __table_args__ = (Index("ix_workout_sessions_user_id_date", "user_id", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    date: Mapped[dt.date]
    name: Mapped[str] = mapped_column(String(100), default="Workout")
    notes: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[dt.datetime | None]
    ended_at: Mapped[dt.datetime | None]
    duration_min: Mapped[int | None]
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("workout_templates.id", ondelete="SET NULL")
    )
    created_at: Mapped[dt.datetime] = _created_at()

    user: Mapped[User] = relationship(back_populates="workout_sessions")
    template: Mapped[WorkoutTemplate | None] = relationship()
    sets: Mapped[list[WorkoutSet]] = relationship(
        back_populates="session", cascade="all, delete-orphan",
        order_by=lambda: (WorkoutSet.exercise_order, WorkoutSet.set_index),
    )
    cardio_entries: Mapped[list[CardioEntry]] = relationship(back_populates="session")


class WorkoutSet(Base):
    """A single set: e.g. Bench Press, set 2, 6 reps x 145 lb."""

    __tablename__ = "workout_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("workout_sessions.id", ondelete="CASCADE"), index=True
    )
    # RESTRICT: an exercise that has logged sets can't be deleted.
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.id", ondelete="RESTRICT"), index=True
    )
    exercise_order: Mapped[int] = mapped_column(default=0)  # position of the exercise in the session
    set_index: Mapped[int] = mapped_column(default=0)
    reps: Mapped[int]
    weight_lb: Mapped[float] = mapped_column(default=0)  # 0 for bodyweight
    rpe: Mapped[float | None]  # rate of perceived exertion, 1-10
    is_warmup: Mapped[bool] = mapped_column(default=False)
    completed_at: Mapped[dt.datetime | None]

    session: Mapped[WorkoutSession] = relationship(back_populates="sets")
    exercise: Mapped[Exercise] = relationship()

    @validates("reps", "weight_lb")
    def _v_numbers(self, k, v):
        return _non_negative(k, v)

    @validates("rpe")
    def _v_rpe(self, _k, v):
        if v is not None and not 1 <= v <= 10:
            raise ValueError(f"RPE must be between 1 and 10 (got {v})")
        return v


class CardioEntry(Base):
    """A cardio activity, optionally linked to a lifting session."""

    __tablename__ = "cardio_entries"
    __table_args__ = (Index("ix_cardio_entries_user_id_date", "user_id", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    date: Mapped[dt.date]
    activity: Mapped[str] = mapped_column(String(20))
    duration_min: Mapped[float]
    distance_mi: Mapped[float | None]
    avg_hr: Mapped[int | None]
    calories_burned: Mapped[float | None]
    calories_estimated: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("workout_sessions.id", ondelete="SET NULL")
    )
    created_at: Mapped[dt.datetime] = _created_at()

    user: Mapped[User] = relationship(back_populates="cardio_entries")
    session: Mapped[WorkoutSession | None] = relationship(back_populates="cardio_entries")

    @validates("activity")
    def _v_activity(self, _k, v):
        return _choice("cardio activity", v, C.CARDIO_ACTIVITIES)

    @validates("duration_min", "distance_mi", "avg_hr", "calories_burned")
    def _v_numbers(self, k, v):
        return _non_negative(k, v)


# ---------------------------------------------------------------------------
# AI coach
# ---------------------------------------------------------------------------
class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = _user_fk()
    title: Mapped[str] = mapped_column(String(200), default="New chat")
    created_at: Mapped[dt.datetime] = _created_at()
    updated_at: Mapped[dt.datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="conversations")
    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan",
        order_by=lambda: ChatMessage.id,
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(10))
    # {"text": "..."} or richer parts (tool calls/results) as the coach needs.
    content: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[dt.datetime] = _created_at()

    conversation: Mapped[Conversation] = relationship(back_populates="messages")

    @validates("role")
    def _v_role(self, _k, v):
        return _choice("role", v, C.CHAT_ROLES)
