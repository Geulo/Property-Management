from src.database import Database

VERSION = "0.0.1"
NAME = "WoW"


db = Database(version=VERSION, name=NAME)
db = Database.connect_sqlite()


def user_table(db = Database):
    
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    print("user_table created")
    
user_table()


    




print("Hello, World!")