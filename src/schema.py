import sqlite3

import bcrypt

from src.database import Database


def create_schema():
    
    connection = Database.connect_sqlite()
    cursor = connection.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        password_hash TEXT NOT NULL
        );
        """)
    
    connection.commit()
    connection.close()
    
def clear_schema():
    connection = Database.connect_sqlite()
    cursor = connection.cursor()

    decision = input("Are you Sure? /y: ")
    if decision == "y":
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")

        print("Database wiped")
    
    else:
        print("exited...")
        
    connection.commit()
    connection.close()
    

create_schema()