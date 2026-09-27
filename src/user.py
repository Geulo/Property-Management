import datetime
import sqlite3

from flask import Blueprint, redirect, render_template, request

from src.database import Database
from src.util import check_password, hash_password

user_bp = Blueprint("user", __name__)

@user_bp.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "GET": #returns signup page
        return render_template("signup.html")
    
    username = request.form["username"]
    email = request.form["email"]
    password_hash = hash_password(request.form["password"])
    
    connection = Database.connect_sqlite()
    cursor = connection.cursor()
    
    try: 
        cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?,?,?);", (username, email, password_hash)
        )
        connection.commit()
        connection.close()
        return redirect ("/signup.html")
    
    except sqlite3.IntegrityError:    
        connection.close()
        return render_template("signup.html", error="Email already registered")
        
@user_bp.route("/login", methods=["GET", "POST"])
def signin():
    
    if request.method == "GET":
        return render_template("login.html")
    
    email = request.form["email"]
    password = request.form["password"]

    
    connection = Database.connect_sqlite()
    cursor = connection.cursor()
    
    try:
        cursor.execute("SELECT password_hash FROM users WHERE email = ?;", (email,))
        user = cursor.fetchone()
        
        if user:
            if check_password(password, user["password_hash"]):
                print(f'User {email} has logged in')
                return redirect("/index")
            else:
                return render_template("login.html", error="Invalid email or pasword...")
        else:
            return render_template("login.html", error="Invalid email or pasword...")
        
    except sqlite3.IntegrityError:
        connection.close()
        return redirect("/login")