import os
import sqlite3
from datetime import datetime, timezone

from flask import redirect

DB_PATH = os.path.join(os.environ.get("DATA_DIR", "data"), "property_management.db")
DB_NAME = "property_management.db"

class Database:
    
    def __init__(self):
        self.connection = None
    
    @staticmethod
    def connect_sqlite():
        connection = sqlite3.connect(DB_PATH)
        connection.row_factory = sqlite3.Row
        print(f'db name: {DB_NAME} connected at {datetime.now(timezone.utc).strftime("%H:%M:%S")}')
        return connection
    
    def close(self):
        if self.connection:
            self.connection.close()

            
    
    def insert(self):
        pass
    
    def delete(self):
        pass