import sqlite3 
import database as db

def create_schema():
    
    database = db.connect_sqlite()
    cursor = database.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
    
    database.commit()
    database.close()
    
    