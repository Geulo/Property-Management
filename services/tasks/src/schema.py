# The tasks service owns only the tasks table. property_id is a plain id: the property
# lives in the property service's database, so there is no foreign key to it, and the
# service checks the property exists (over HTTP) when a task is added.
# user_id is the owner, copied from the login token, so listing and changing tasks
# never needs the property service.
#
# Each statement checks whether its table exists first, so this is safe to run on every
# startup. Versioned migrations replace this file in a later step (Assignment 2 §4).
SCHEMA = [
    """
    IF OBJECT_ID('tasks', 'U') IS NULL
    CREATE TABLE tasks (
        task_id INT IDENTITY(1, 1) PRIMARY KEY,
        task_name NVARCHAR(80) NOT NULL,
        description NVARCHAR(1000),
        status NVARCHAR(20) NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'in_progress', 'done')),
        priority NVARCHAR(20) NOT NULL DEFAULT 'normal'
            CHECK (priority IN ('low', 'normal', 'urgent')),
        property_id INT NOT NULL,
        user_id INT NOT NULL,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    )
    """,
    # one row that /health updates, to prove the service can write to its database
    """
    IF OBJECT_ID('health_probe', 'U') IS NULL
    CREATE TABLE health_probe (
        probe_id INT PRIMARY KEY,
        checked_at DATETIME2 NOT NULL
    )
    """,
    """
    IF NOT EXISTS (SELECT 1 FROM health_probe)
    INSERT INTO health_probe (probe_id, checked_at) VALUES (1, SYSUTCDATETIME())
    """,
]


def create_schema(connection):
    cursor = connection.cursor()
    for statement in SCHEMA:
        cursor.execute(statement)
    connection.commit()


def check_database(connection):
    # write, then read back: /health is only "ok" if both work
    cursor = connection.cursor()
    cursor.execute("UPDATE health_probe SET checked_at = SYSUTCDATETIME() WHERE probe_id = 1")
    connection.commit()
    cursor.execute("SELECT checked_at FROM health_probe WHERE probe_id = 1")
    return cursor.fetchone() is not None
