"""Built-in data loaded at startup (the exercise library)."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import PROJECT_ROOT
from core.models import Exercise

EXERCISES_PATH = PROJECT_ROOT / "data" / "exercises.json"


def load_exercise_library(path: Path = EXERCISES_PATH) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def seed_exercises(session: Session, path: Path = EXERCISES_PATH) -> int:
    """Add built-in exercises that aren't in the database yet.

    Safe to run on every startup; adding an entry to exercises.json adds it
    to the app next launch. Returns how many were added.
    """
    existing = set(
        session.scalars(select(Exercise.name).where(Exercise.created_by_user_id.is_(None)))
    )
    added = 0
    for item in load_exercise_library(path):
        if item["name"] in existing:
            continue
        session.add(Exercise(
            name=item["name"],
            primary_muscle=item["primary"],
            secondary_muscles=item.get("secondary", []),
            equipment=item["equipment"],
        ))
        existing.add(item["name"])
        added += 1
    return added
