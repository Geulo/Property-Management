from flask import Flask, render_template, request, redirect
import sqlite3
import bcrypt

from src.database import Database

VERSION = "0.0.1"
NAME = "WoW"

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("login.html") 

@app.route("/signup", methods=["GET", "POST"])
def signup(db = Database):
    
    if request.method == "GET": #returns signup page
        return render_template("signup.html")
    
    username = request.form["username"]
    email = request.form["email"]
    password = request.form["password"]
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    connection = db.connect_sqlite()
    cursor = connection.cursor()
    
    try: 
        cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?,?,?);", (username, email, password_hash)
        )
        
        connection.commit()
        connection.close()
        return redirect ("/index.html")
    
    except sqlite3.IntegrityError:
        
        connection.close()
        return render_template("signup.html", error="Email already registered")
        
        
    


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)