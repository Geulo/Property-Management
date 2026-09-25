import sqlite3
from datetime import datetime, timezone
 
DB_PATH = "data/property_management.db"
DB_NAME = "property_management.db"
class Database:
    
    def __init__(self, version, name):
        self.version = version
        self.name = name
    
    @staticmethod
    def connect_sqlite():
         if sqlite3.connect(DB_PATH):
             return print(f'db name: {DB_NAME} connected at {datetime.now(timezone.utc).strftime("%H:%M:%S")}')
        

    @staticmethod
    def cursor():
        return sqlite3.Cursor(sqlite3.connect(DB_PATH))

                    
    def create_table(self):
        pass
    
    def insert(self):
        pass
    
    def delete(self):
        pass