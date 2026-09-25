import database as db

database = db.connect_sqlite()
cursor = db.cursor()

cursor.execute("""
               CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENET,
                email = TEXT NOT NULL UNIQUE
                create_at TEXT DEFAULT CURRENT_TIMESTAMP              
                   
                   
               )
    
               """)
    




print("Hello, World!")