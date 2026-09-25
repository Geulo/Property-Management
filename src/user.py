import sqlite3
import datetime

class User:
    
    def __init__(self, username, email, role, created_at, first_name = None, last_name = None, company=None):
        self.username = username
        self.email = email
        self.created_at = None
        self.role = role
        self.first_name = first_name
        self.last_name = last_name
        self.company = company 
        
    def add_user(self):
        
        self.username = input("Enter username: ")
        self.email = input("Email: ")
        self.role = input("Email")
        
        pass
    
        def add_user(self, username, email, db = database, time = datetime):
        self.username = username
        self.email = email
        self.created_at = 