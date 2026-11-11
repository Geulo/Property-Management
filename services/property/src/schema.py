# The property service owns users and properties. Tasks live in the tasks service's
# own database and point at a property by its plain id (no foreign key across the seam).
#
# Each statement checks whether its table exists first, so this is safe to run on every
# startup. Versioned migrations replace this file in a later step (Assignment 2 §4).
SCHEMA = [
    """
    IF OBJECT_ID('users', 'U') IS NULL
    CREATE TABLE users (
        user_id INT IDENTITY(1, 1) PRIMARY KEY,
        username NVARCHAR(100) NOT NULL,
        email NVARCHAR(255) NOT NULL UNIQUE,
        password_hash NVARCHAR(100) NOT NULL,
        created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
    )
    """,
    """
    IF OBJECT_ID('properties', 'U') IS NULL
    CREATE TABLE properties (
        property_id INT IDENTITY(1, 1) PRIMARY KEY,
        property_name NVARCHAR(50) NOT NULL,
        address NVARCHAR(255) NOT NULL,
        user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE
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
