import os
import time
from urllib.parse import unquote, urlparse

import pymssql


def parse_database_url(url):
    # mssql://user:password@host:1433/database -> keyword arguments for pymssql.connect
    parts = urlparse(url)
    return {
        "server": parts.hostname,
        "port": parts.port or 1433,
        "user": unquote(parts.username or ""),
        "password": unquote(parts.password or ""),
        "database": parts.path.lstrip("/"),
    }


class Database:

    @staticmethod
    def connect(url=None, attempts=None):
        # DATABASE_URL is read at call time so tests / deployment can point it elsewhere.
        # Retries with backoff: SQL Server takes ~20 s to start in compose, and a paused
        # Azure SQL serverless database refuses connections for up to a minute (error 40613).
        settings = parse_database_url(url or os.environ["DATABASE_URL"])
        attempts = attempts or int(os.environ.get("DB_CONNECT_ATTEMPTS", "8"))
        for attempt in range(1, attempts + 1):
            try:
                # as_dict makes every row a dict, so row["email"] works like sqlite3.Row did
                return pymssql.connect(**settings, as_dict=True, login_timeout=10)
            except pymssql.OperationalError:
                if attempt == attempts:
                    raise
                time.sleep(min(2 ** attempt, 15))


# pymssql connections have no execute() shortcut like sqlite3, so these three cover it.
# Placeholders are %s, not ? as in SQLite.

def fetch_all(connection, sql, params=None):
    cursor = connection.cursor()
    cursor.execute(sql, params)
    return cursor.fetchall()


def fetch_one(connection, sql, params=None):
    cursor = connection.cursor()
    cursor.execute(sql, params)
    return cursor.fetchone()


def execute(connection, sql, params=None):
    # runs a write and commits it; returns the number of rows it changed
    cursor = connection.cursor()
    cursor.execute(sql, params)
    connection.commit()
    return cursor.rowcount
