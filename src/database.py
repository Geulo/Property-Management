import os
import sqlite3

DB_NAME = "property_management.db"


def get_db_path():
    # DATA_DIR is read at call time so tests / deployment can point it elsewhere
    data_dir = os.environ.get("DATA_DIR", "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, DB_NAME)


class Database:

    @staticmethod
    def connect_sqlite(path=None):
        connection = sqlite3.connect(path or get_db_path())
        connection.row_factory = sqlite3.Row
        # sqlite has foreign keys OFF by default, needed for ON DELETE CASCADE
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
