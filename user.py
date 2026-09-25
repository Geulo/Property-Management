import sqlite3

class User:
    
    def __init__(self, username, email, role, first_name = None, last_name = None, company=None):
        self.username = username
        self.email = email
        self.role = role
        self.first_name = first_name
        self.last_name = last_name
        self.company = company 
        
    def add_user(self):
        
        
    