from flask import Blueprint, g, jsonify, request

from src.auth import require_user
from src.database import Database, execute, fetch_all, fetch_one

property_bp = Blueprint("property_bp", __name__)

MAX_NAME_LENGTH = 50
MAX_UNITS = 500

COLUMNS = "property_id, property_name, address, units, user_id"


# ---- logic (no Flask, takes a connection so it can be unit tested) ----

def add_property(connection, user_id, property_name, address, units=1):
    property_name = (property_name or "").strip()
    address = (address or "").strip()

    if not property_name or not address:
        raise ValueError("Property name and address are required")
    if len(property_name) > MAX_NAME_LENGTH:
        raise ValueError(f"Property name must be at most {MAX_NAME_LENGTH} characters")
    # bool is an int in Python, so it is ruled out by name; "3" from a form is not accepted either
    if type(units) is not int or not 1 <= units <= MAX_UNITS:
        raise ValueError(f"Units must be a whole number from 1 to {MAX_UNITS}")

    row = fetch_one(
        connection,
        "INSERT INTO properties (property_name, address, units, user_id) OUTPUT INSERTED.property_id "
        "VALUES (%s, %s, %s, %s)",
        (property_name, address, units, user_id),
    )
    connection.commit()
    return row["property_id"]


def list_properties(connection, user_id):
    return fetch_all(
        connection,
        f"SELECT {COLUMNS} FROM properties WHERE user_id = %s ORDER BY property_name",
        (user_id,),
    )


def get_property(connection, property_id, user_id):
    # filtering on user_id means a user can never load someone else's property
    return fetch_one(
        connection,
        f"SELECT {COLUMNS} FROM properties WHERE property_id = %s AND user_id = %s",
        (property_id, user_id),
    )


def delete_property(connection, property_id, user_id):
    # the property's tasks live in the tasks service: the UI deletes them first (ADR-7)
    return execute(
        connection,
        "DELETE FROM properties WHERE property_id = %s AND user_id = %s",
        (property_id, user_id),
    ) == 1


# ---- routes (JSON for the static UI and the tasks service) ----

@property_bp.route("/properties")
@require_user
def index():
    connection = Database.connect()
    properties = list_properties(connection, g.user_id)
    connection.close()
    return jsonify(properties=properties)


@property_bp.route("/properties", methods=["POST"])
@require_user
def create_property():
    body = request.get_json(silent=True) or {}
    connection = Database.connect()
    try:
        property_id = add_property(
            connection, g.user_id, body.get("property_name"), body.get("address"), body.get("units", 1)
        )
        created = get_property(connection, property_id, g.user_id)
    except ValueError as error:
        return jsonify(error=str(error)), 400
    finally:
        connection.close()

    return jsonify(created), 201


# The endpoint the tasks service calls across the seam before it adds a task.
@property_bp.route("/properties/<int:property_id>")
@require_user
def show_property(property_id):
    connection = Database.connect()
    found = get_property(connection, property_id, g.user_id)
    connection.close()

    if found is None:
        return jsonify(error="Property not found"), 404
    return jsonify(found)


@property_bp.route("/properties/<int:property_id>", methods=["DELETE"])
@require_user
def remove_property(property_id):
    connection = Database.connect()
    deleted = delete_property(connection, property_id, g.user_id)
    connection.close()

    if not deleted:
        return jsonify(error="Property not found"), 404
    return "", 204
