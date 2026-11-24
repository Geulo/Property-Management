import pytest

from src.database import fetch_all
from src.migrations import apply_migrations


@pytest.fixture
def scratch_versions(connection):
    # test migrations are named 9xx_*.sql and their records removed afterwards
    yield
    connection.cursor().execute("DELETE FROM schema_migrations WHERE version LIKE '9%'")
    connection.commit()


def recorded(connection):
    return [row["version"] for row in fetch_all(connection, "SELECT version FROM schema_migrations")]


def test_init_is_recorded(connection):
    assert "001_init.sql" in recorded(connection)


def test_second_boot_applies_nothing(connection):
    assert apply_migrations(connection) == []


def test_new_migrations_run_once_in_name_order(connection, scratch_versions, tmp_path):
    # a temp table (#name) vanishes with the connection, so the test leaves no tables behind
    (tmp_path / "902_second.sql").write_text("INSERT INTO #order_check (step) VALUES (2)")
    (tmp_path / "901_first.sql").write_text("CREATE TABLE #order_check (step INT)")
    assert apply_migrations(connection, tmp_path) == ["901_first.sql", "902_second.sql"]
    assert apply_migrations(connection, tmp_path) == []


def test_failed_migration_is_not_recorded(connection, scratch_versions, tmp_path):
    (tmp_path / "903_broken.sql").write_text("SELECT * FROM table_that_does_not_exist")
    with pytest.raises(Exception):
        apply_migrations(connection, tmp_path)
    assert "903_broken.sql" not in recorded(connection)
