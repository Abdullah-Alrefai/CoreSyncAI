import pytest

from core.auth import AuthError, authenticate, create_user


def test_password_is_hashed_and_profile_created(session):
    user = create_user(session, "Abdullah", "supersecret")
    assert user.username == "abdullah"
    assert user.password_hash != "supersecret"
    assert user.password_hash.startswith("$2")  # bcrypt
    assert user.profile is not None
    assert user.profile.goal == "maintain"


def test_authenticate(session):
    create_user(session, "lifter", "supersecret")
    assert authenticate(session, "lifter", "supersecret") is not None
    assert authenticate(session, "LIFTER ", "supersecret") is not None  # case/space-insensitive
    assert authenticate(session, "lifter", "wrongpassword") is None
    assert authenticate(session, "nobody", "supersecret") is None


def test_duplicate_username_rejected_case_insensitively(session):
    create_user(session, "lifter", "supersecret")
    with pytest.raises(AuthError, match="taken"):
        create_user(session, "Lifter", "anotherpass")


@pytest.mark.parametrize("bad", ["ab", "has space", "emoji💪", "x" * 31, ""])
def test_invalid_usernames(session, bad):
    with pytest.raises(AuthError):
        create_user(session, bad, "supersecret")


def test_password_length_limits(session):
    with pytest.raises(AuthError, match="at least"):
        create_user(session, "lifter", "short")
    with pytest.raises(AuthError, match="too long"):
        create_user(session, "lifter", "x" * 73)
