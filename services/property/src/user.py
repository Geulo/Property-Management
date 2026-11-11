import pymssql
from flask import Blueprint, current_app, jsonify, request

from src.auth import make_token
from src.database import Database, fetch_one
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
        # OUTPUT INSERTED.<id> is SQL Server's way to hand back the new IDENTITY value
        row = fetch_one(
            connection,
            "INSERT INTO users (username, email, password_hash) OUTPUT INSERTED.user_id "
            "VALUES (%s, %s, %s)",
            (username, email, hash_password(password)),
        )
        connection.commit()
    except pymssql.IntegrityError:
        connection.rollback()
        raise ValueError("Email already registered")

    return row["user_id"]


def authenticate(connection, email, password):
    email = (email or "").strip().lower()
    user = fetch_one(
        connection,
        "SELECT user_id, username, password_hash FROM users WHERE email = %s",
        (email,),
    )

    if user and check_password(password or "", user["password_hash"]):
        return user
    return None


# ---- routes (JSON for the static UI) ----

@user_bp.route("/signup", methods=["POST"])
def signup():
    body = request.get_json(silent=True) or {}
    connection = Database.connect()
    try:
        user_id = create_user(connection, body.get("username"), body.get("email"), body.get("password"))
    except ValueError as error:
        return jsonify(error=str(error)), 400
    finally:
        connection.close()

    return jsonify(user_id=user_id), 201


@user_bp.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    connection = Database.connect()
    user = authenticate(connection, body.get("email"), body.get("password"))
    connection.close()

    if user is None:
        return jsonify(error="Invalid email or password"), 401

    token = make_token(current_app.config["SECRET_KEY"], user["user_id"])
    return jsonify(token=token, user_id=user["user_id"], username=user["username"])
