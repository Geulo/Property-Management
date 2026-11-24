import logging
import re
from pathlib import Path

# Versioned migrations: every file in migrations/ (001_init.sql, 002_...) runs once, in order of
# its name, at startup. The ones already applied are recorded in schema_migrations, so a second
# boot applies nothing. Applied files are never edited: a correction is a new file.
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"

log = logging.getLogger("service")

# A line holding only GO ends a batch, as in sqlcmd and SSMS. SQL Server compiles a whole batch
# before running it, so a statement that uses a column added earlier in the file must be in a
# later batch.
BATCH_SEPARATOR = re.compile(r"^\s*GO\s*$", re.IGNORECASE | re.MULTILINE)


def applied_versions(connection):
    cursor = connection.cursor()
    cursor.execute(
        """
        IF OBJECT_ID('schema_migrations', 'U') IS NULL
        CREATE TABLE schema_migrations (
            version NVARCHAR(255) PRIMARY KEY,
            applied_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
        )
        """
    )
    connection.commit()
    cursor.execute("SELECT version FROM schema_migrations")
    return {row["version"] for row in cursor.fetchall()}


def apply_migrations(connection, migrations_dir=MIGRATIONS_DIR):
    # Returns the names of the files it applied (empty on a second boot).
    # Safe only with one replica at a time: two containers starting together could both try
    # the same file. Container Apps is set to at most one replica for that reason.
    done = applied_versions(connection)
    applied = []
    for path in sorted(migrations_dir.glob("*.sql")):
        if path.name in done:
            continue
        cursor = connection.cursor()
        try:
            # the file and its record commit together: a failed migration leaves no record and
            # no half-applied change, and the service refuses to start until it is fixed
            for batch in BATCH_SEPARATOR.split(path.read_text()):
                if batch.strip():
                    cursor.execute(batch)
            cursor.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.name,))
            connection.commit()
        except Exception:
            connection.rollback()
            log.error("migration %s failed, nothing from it was applied", path.name)
            raise
        log.info("applied migration %s", path.name)
        applied.append(path.name)
    if not applied:
        log.info("migrations up to date (%d applied before)", len(done))
    return applied


def check_database(connection):
    # write, then read back: /health is only "ok" if both work
    cursor = connection.cursor()
    cursor.execute("UPDATE health_probe SET checked_at = SYSUTCDATETIME() WHERE probe_id = 1")
    connection.commit()
    cursor.execute("SELECT checked_at FROM health_probe WHERE probe_id = 1")
    return cursor.fetchone() is not None
