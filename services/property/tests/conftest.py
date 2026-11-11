import pytest

from src.database import Database
from src.schema import create_schema
from src.user import create_user


@pytest.fixture
def connection():
    # fresh in-memory database per test, so tests never touch data/
    connection = Database.connect_sqlite(":memory:")
    create_schema(connection)
    yield connection
    connection.close()


@pytest.fixture
def user_id(connection):
    return create_user(connection, "landlord", "landlord@example.com", "password123")


@pytest.fixture
def other_user_id(connection):
    return create_user(connection, "other", "other@example.com", "password123")
