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


def test_002_keeps_existing_tasks_and_backfills_them(connection, tmp_path):
    # Replays 001 then 002 on an empty database, with a task inserted in between: the same
    # order as on Azure, where tasks existed before 002 was deployed.
    from conftest import TEST_DATABASE_URL, ensure_database
    from src.database import Database, fetch_one
    from src.migrations import MIGRATIONS_DIR

    url = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/tasks_migration_test"
    ensure_database(url)
    fresh = Database.connect(url, attempts=1)
    cursor = fresh.cursor()
    cursor.execute("IF OBJECT_ID('tasks', 'U') IS NOT NULL DROP TABLE tasks")
    cursor.execute("IF OBJECT_ID('health_probe', 'U') IS NOT NULL DROP TABLE health_probe")
    cursor.execute("IF OBJECT_ID('schema_migrations', 'U') IS NOT NULL DROP TABLE schema_migrations")
    fresh.commit()

    first = tmp_path / "001_init.sql"
    first.write_text((MIGRATIONS_DIR / "001_init.sql").read_text())
    apply_migrations(fresh, tmp_path)
    cursor.execute(
        "INSERT INTO tasks (task_name, priority, property_id, user_id, created_at) "
        "VALUES ('Fix boiler', 'urgent', 10, 1, '2026-11-01T09:00:00')"
    )
    fresh.commit()

    second = tmp_path / "002_add_task_updated_at.sql"
    second.write_text((MIGRATIONS_DIR / "002_add_task_updated_at.sql").read_text())
    assert apply_migrations(fresh, tmp_path) == ["002_add_task_updated_at.sql"]

    task = fetch_one(fresh, "SELECT task_name, priority, created_at, updated_at FROM tasks")
    assert task["task_name"] == "Fix boiler" and task["priority"] == "urgent"
    assert task["updated_at"] == task["created_at"]
    fresh.close()
