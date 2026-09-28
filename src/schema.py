from src.database import Database


def create_schema():
    
    connection = Database.connect_sqlite()
    cursor = connection.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NULL,
            email TEXT NOT NULL UNIQUE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            password_hash TEXT NOT NULL,
            role_id FOREIGN KEY (role_id),
            property_id FOREIGN KEY (property_id),
            REFERENCES roles(role_id), properties(property_id)

        );
        
        CREATE TABLE IF NOT EXISTS credentials (
            credential_id INTEGER PRIMARY KEY AUTOINCREMENT,
            credential_level INT CHECK(credential_level >= 2 || credential_level <= 0),
            credential_level_name VARCHAR (10),
            name VARCHAR(25),
            
        );
        
        CREATE TABLE IF NOT EXISTS roles (
            role_id INTEGER PRIMARY KEY AUTOINCEMENT
            role_name VARCHAR(25),
            credential_id FOREIGN KEY (credential_id),
            REFERENCES credentials(credential_id);
        )
        
        CREATE TABLE IF NOT EXISTS properties (
            property_id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_name VARCHAR(25),
            user_id FOREIGN KEY (user_id),
            REFERENCES users(user_id)
        );
        
        CREATE TABLE IF NOT EXISTS tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name VARCHAR (50),
            property_id FOREIGN KEY (property_id),
            user_id FOREIGN KEY (user_id),
            REFERENCES properties(property_id), users(user_id)

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