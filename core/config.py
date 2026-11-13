"""App settings.

Each value is read from an environment variable first, then from
.streamlit/secrets.toml (gitignored), then falls back to a default.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SECRETS_PATH = PROJECT_ROOT / ".streamlit" / "secrets.toml"
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "coresync.db"


@dataclass(frozen=True)
class Settings:
    database_url: str
    gemini_api_key: str | None
    gemini_model: str
    usda_api_key: str


def _load_secrets() -> dict:
    if not SECRETS_PATH.exists():
        return {}
    with SECRETS_PATH.open("rb") as f:
        return tomllib.load(f)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    secrets = _load_secrets()

    def get(name: str, default: str | None = None) -> str | None:
        return os.getenv(name) or secrets.get(name) or default

    return Settings(
        database_url=get("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"),
        gemini_api_key=get("GEMINI_API_KEY"),
        # Placeholder: confirm the current free-tier model name before use.
        gemini_model=get("GEMINI_MODEL", "gemini-2.5-flash"),
        # DEMO_KEY works for light use; a free personal key raises the limits.
        usda_api_key=get("USDA_API_KEY", "DEMO_KEY"),
    )
