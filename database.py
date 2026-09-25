import sqlite3
 
DATABASE = "property_management.db"
class Database:
    
    def __init__(self, database):
        self.database = self.connect_sqlite()
        self.cursor = self.cursor()
    
    def connect_sqlite(self):
        return sqlite3.connect(DATABASE)

    def cursor(self):
        return self.database.cursor()

                    
    def create_table(self):
        pass
    
    def insert(self):
        pass
    
    def delete(self):
        pass