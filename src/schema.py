import sqlite3 
import database as db

try:
    pass

def schema():
    
    Database = db.connect_sqlite()
    cursor = Database.cursor()
    
    cursor 