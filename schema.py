import sqlite3 
import database as db

class Schema:
    
    def __init__(self, version, date, cursor = db):
        self.cursor = cursor
        self.version = version
        self.date = date
        
    def schema_tables(self):
        
        if 
        self.cursor 