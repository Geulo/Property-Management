import sqlite3

from flask import Blueprint, redirect, render_template, request, session

from src.database import Database
from src.util import check_password, hash_password

user_bp = Blueprint("user", __name__)

MIN_PASSWORD_LENGTH = 8


# ---- logic (no Flask, takes a connection so it can be unit tested) ----

def create_user(connection, username, email, password):
    username = (username or "").strip()
    email = (email or "").strip().lower()

    if not username or not email or not password:
        raise ValueError("Username, email and password are required")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")

    try:
        cursor = connection.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, hash_password(password)),
        )
        connection.commit()
    except sqlite3.IntegrityError:
        raise ValueError("Email already registered")

    return cursor.lastrowid


def authenticate(connection, email, password):
    email = (email or "").strip().lower()
    user = connection.execute(
        "SELECT user_id, password_hash FROM users WHERE email = ?", (email,)
    ).fetchone()

    if user and check_password(password or "", user["password_hash"]):
        return user["user_id"]
    return None


# ---- routes ----

@user_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")

    connection = Database.connect_sqlite()
    try:
        create_user(
            connection,
            request.form.get("username"),
            request.form.get("email"),
            request.form.get("password"),
        )
    except ValueError as error:
        return render_template("signup.html", error=str(error))
    finally:
        connection.close()

    return redirect("/login")


@user_bp.route("/login", methods=["GET", "POST"])
def signin():
    if request.method == "GET":
        return render_template("login.html")

    connection = Database.connect_sqlite()
    user_id = authenticate(connection, request.form.get("email"), request.form.get("password"))
    connection.close()

    if user_id is None:
        return render_template("login.html", error="Invalid email or password")

    session["user_id"] = user_id
    return redirect("/")


@user_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
