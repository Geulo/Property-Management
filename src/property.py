from flask import Blueprint, abort, redirect, render_template, request, session

from src.database import Database

property_bp = Blueprint("property_bp", __name__)

MAX_NAME_LENGTH = 50


# ---- logic (no Flask, takes a connection so it can be unit tested) ----

def add_property(connection, user_id, property_name, address):
    property_name = (property_name or "").strip()
    address = (address or "").strip()

    if not property_name or not address:
        raise ValueError("Property name and address are required")
    if len(property_name) > MAX_NAME_LENGTH:
        raise ValueError(f"Property name must be at most {MAX_NAME_LENGTH} characters")

    cursor = connection.execute(
        "INSERT INTO properties (property_name, address, user_id) VALUES (?, ?, ?)",
        (property_name, address, user_id),
    )
    connection.commit()
    return cursor.lastrowid


def list_properties(connection, user_id):
    return connection.execute(
        "SELECT * FROM properties WHERE user_id = ? ORDER BY property_name", (user_id,)
    ).fetchall()


def get_property(connection, property_id, user_id):
    # filtering on user_id means a user can never load someone else's property
    return connection.execute(
        "SELECT * FROM properties WHERE property_id = ? AND user_id = ?",
        (property_id, user_id),
    ).fetchone()


def delete_property(connection, property_id, user_id):
    cursor = connection.execute(
        "DELETE FROM properties WHERE property_id = ? AND user_id = ?",
        (property_id, user_id),
    )
    connection.commit()
    return cursor.rowcount == 1


# ---- routes ----

@property_bp.before_request
def require_login():
    if "user_id" not in session:
        return redirect("/login")


@property_bp.route("/")
def index():
    connection = Database.connect_sqlite()
    properties = list_properties(connection, session["user_id"])
    connection.close()
    return render_template("index.html", properties=properties)


@property_bp.route("/properties", methods=["POST"])
def create_property():
    connection = Database.connect_sqlite()
    try:
        add_property(
            connection,
            session["user_id"],
            request.form.get("property_name"),
            request.form.get("address"),
        )
    except ValueError as error:
        properties = list_properties(connection, session["user_id"])
        return render_template("index.html", properties=properties, error=str(error))
    finally:
        connection.close()

    return redirect("/")


@property_bp.route("/properties/<int:property_id>/delete", methods=["POST"])
def remove_property(property_id):
    connection = Database.connect_sqlite()
    deleted = delete_property(connection, property_id, session["user_id"])
    connection.close()

    if not deleted:
        abort(404)
    return redirect("/")
