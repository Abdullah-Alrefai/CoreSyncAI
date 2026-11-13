"""Sign-up and login with bcrypt-hashed passwords."""

from __future__ import annotations

import re

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models import Profile, User

USERNAME_PATTERN = re.compile(r"^[a-z0-9_.-]{3,30}$")
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72  # bcrypt's limit

# Checked against when the username doesn't exist, so a wrong username takes
# as long as a wrong password (doesn't reveal which usernames exist).
_DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt()).decode()


class AuthError(ValueError):
    """Raised with a message that is safe to show the user."""


def normalize_username(username: str) -> str:
    return username.strip().lower()


def validate_username(username: str) -> str:
    name = normalize_username(username)
    if not USERNAME_PATTERN.fullmatch(name):
        raise AuthError(
            "Username must be 3-30 characters: letters, numbers, dots, dashes or underscores."
        )
    return name


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise AuthError(f"Password is too long (max {MAX_PASSWORD_BYTES} bytes).")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:  # malformed hash or over-long password
        return False


def get_user_by_username(session: Session, username: str) -> User | None:
    return session.scalar(select(User).where(User.username == normalize_username(username)))


def create_user(session: Session, username: str, password: str) -> User:
    """Create a user (with an empty profile). Raises AuthError if invalid or taken."""
    name = validate_username(username)
    validate_password(password)
    if get_user_by_username(session, name) is not None:
        raise AuthError("That username is already taken.")

    user = User(username=name, password_hash=hash_password(password))
    user.profile = Profile()
    session.add(user)
    session.flush()  # assigns user.id
    return user


def authenticate(session: Session, username: str, password: str) -> User | None:
    """Return the user if the credentials are correct, otherwise None."""
    user = get_user_by_username(session, username)
    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None
    return user if verify_password(password, user.password_hash) else None
