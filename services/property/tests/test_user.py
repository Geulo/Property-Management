import pytest

from src.user import authenticate, create_user


def test_create_user_returns_id(connection):
    assert create_user(connection, "ruben", "ruben@example.com", "password123") > 0


def test_password_is_hashed_not_stored_plain(connection):
    create_user(connection, "ruben", "ruben@example.com", "password123")
    stored = connection.execute("SELECT password_hash FROM users").fetchone()[0]
    assert stored != "password123"


def test_email_is_normalised(connection):
    create_user(connection, "ruben", "  Ruben@Example.COM ", "password123")
    assert authenticate(connection, "ruben@example.com", "password123") is not None


def test_duplicate_email_rejected(connection):
    create_user(connection, "ruben", "ruben@example.com", "password123")
    with pytest.raises(ValueError, match="already registered"):
        create_user(connection, "someone", "ruben@example.com", "password456")


@pytest.mark.parametrize("username, email, password", [
    ("", "a@example.com", "password123"),
    ("ruben", "", "password123"),
    ("ruben", "a@example.com", ""),
    (None, None, None),
])
def test_missing_fields_rejected(connection, username, email, password):
    with pytest.raises(ValueError, match="required"):
        create_user(connection, username, email, password)


def test_short_password_rejected(connection):
    with pytest.raises(ValueError, match="at least 8"):
        create_user(connection, "ruben", "ruben@example.com", "short")


def test_authenticate_correct_password(connection, user_id):
    assert authenticate(connection, "landlord@example.com", "password123") == user_id


def test_authenticate_wrong_password(connection, user_id):
    assert authenticate(connection, "landlord@example.com", "wrong-password") is None


def test_authenticate_unknown_email(connection):
    assert authenticate(connection, "nobody@example.com", "password123") is None
