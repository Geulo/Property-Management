import os

import pymssql
import pytest

from src.database import Database, parse_database_url
from src.schema import create_schema
from src.user import create_user

# Tests that touch the database need a SQL Server, e.g. the one from docker compose:
#   TEST_DATABASE_URL=mssql://sa:<SA_PASSWORD>@localhost:1433/property_test
# Without it they are skipped, and only the tests that need no database run.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def ensure_database(url):
    # create the test database on first use (connects to master, CREATE DATABASE can't run in a transaction)
    settings = parse_database_url(url)
    name = settings.pop("database")
    with pymssql.connect(**settings, database="master", autocommit=True) as master:
        master.cursor().execute(f"IF DB_ID('{name}') IS NULL CREATE DATABASE [{name}]")


@pytest.fixture
def connection():
    if not TEST_DATABASE_URL:
        pytest.skip("needs SQL Server: set TEST_DATABASE_URL")
    ensure_database(TEST_DATABASE_URL)
    connection = Database.connect(TEST_DATABASE_URL, attempts=1)
    create_schema(connection)
    # empty tables per test, so every test starts from the same state
    cursor = connection.cursor()
    cursor.execute("DELETE FROM properties")
    cursor.execute("DELETE FROM users")
    connection.commit()
    yield connection
    connection.close()


@pytest.fixture
def user_id(connection):
    return create_user(connection, "landlord", "landlord@example.com", "password123")


@pytest.fixture
def other_user_id(connection):
    return create_user(connection, "other", "other@example.com", "password123")
