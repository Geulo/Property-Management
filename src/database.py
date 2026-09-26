import sqlite3
from datetime import datetime, timezone
 
DB_PATH = "data/property_management.db"
DB_NAME = "property_management.db"
class Database:
    
    def __init__(self):
        self.conn = None
    
    @staticmethod
    def connect_sqlite():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        print(f'db name: {DB_NAME} connected at {datetime.now(timezone.utc).strftime("%H:%M:%S")}')
        return conn
    
    def close(self):
        if self.conn:
            self.conn.close()

                    
    def create_table(self):
        pass
    
    def insert(self):
        pass
    
    def delete(self):
        pass