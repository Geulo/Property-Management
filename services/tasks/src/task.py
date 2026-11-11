from flask import Blueprint, g, jsonify, request

from src.auth import require_user
from src.database import Database, execute, fetch_all, fetch_one

# The ONLY dependency on the property domain, now over HTTP instead of an import.
from src.property_client import PropertyServiceUnavailable, fetch_property

task_bp = Blueprint("task_bp", __name__)

STATUSES = ("pending", "in_progress", "done")
PRIORITIES = ("low", "normal", "urgent")

# which status a task is allowed to move to from its current status
ALLOWED_TRANSITIONS = {
    "pending": ("in_progress", "done"),
    "in_progress": ("pending", "done"),
    "done": ("pending",),  # re-open a task that came back
}

MAX_TASK_NAME_LENGTH = 80

COLUMNS = "task_id, task_name, description, status, priority, property_id"


# ---- logic (no Flask, takes a connection so it can be unit tested) ----

def add_task(connection, user_id, property_id, task_name, description="", priority="normal"):
    task_name = (task_name or "").strip()
    description = (description or "").strip()

    if not task_name:
        raise ValueError("Task name is required")
    if len(task_name) > MAX_TASK_NAME_LENGTH:
        raise ValueError(f"Task name must be at most {MAX_TASK_NAME_LENGTH} characters")
    if priority not in PRIORITIES:
        raise ValueError(f"Priority must be one of {', '.join(PRIORITIES)}")

    row = fetch_one(
        connection,
        "INSERT INTO tasks (task_name, description, priority, property_id, user_id) "
        "OUTPUT INSERTED.task_id VALUES (%s, %s, %s, %s, %s)",
        (task_name, description, priority, property_id, user_id),
    )
    connection.commit()
    return row["task_id"]


def list_tasks(connection, user_id, property_id):
    # open tasks first, then urgent before normal before low, newest first
    return fetch_all(
        connection,
        f"""
        SELECT {COLUMNS} FROM tasks WHERE property_id = %s AND user_id = %s
        ORDER BY
            CASE status WHEN 'done' THEN 1 ELSE 0 END,
            CASE priority WHEN 'urgent' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END,
            task_id DESC
        """,
        (property_id, user_id),
    )


def get_task(connection, user_id, property_id, task_id):
    return fetch_one(
        connection,
        f"SELECT {COLUMNS} FROM tasks WHERE task_id = %s AND property_id = %s AND user_id = %s",
        (task_id, property_id, user_id),
    )


def can_transition(current_status, new_status):
    return new_status in ALLOWED_TRANSITIONS.get(current_status, ())


def update_status(connection, user_id, property_id, task_id, new_status):
    if new_status not in STATUSES:
        raise ValueError(f"Status must be one of {', '.join(STATUSES)}")

    task = get_task(connection, user_id, property_id, task_id)
    if task is None:
        raise LookupError("Task not found")
    if not can_transition(task["status"], new_status):
        raise ValueError(f"Cannot move task from {task['status']} to {new_status}")

    execute(connection, "UPDATE tasks SET status = %s WHERE task_id = %s", (new_status, task_id))


def delete_task(connection, user_id, property_id, task_id):
    return execute(
        connection,
        "DELETE FROM tasks WHERE task_id = %s AND property_id = %s AND user_id = %s",
        (task_id, property_id, user_id),
    ) == 1


def summarize(tasks):
    # pure function: counts per status + open urgent tasks, shown on the property page
    summary = {status: 0 for status in STATUSES}
    summary["urgent_open"] = 0
    for task in tasks:
        summary[task["status"]] += 1
        if task["priority"] == "urgent" and task["status"] != "done":
            summary["urgent_open"] += 1
    return summary


# ---- routes (JSON for the static UI) ----

@task_bp.route("/properties/<int:property_id>/tasks")
@require_user
def property_tasks(property_id):
    # served from this service's own database only, so it works while property is down
    connection = Database.connect()
    tasks = list_tasks(connection, g.user_id, property_id)
    connection.close()

    for task in tasks:
        task["next_statuses"] = list(ALLOWED_TRANSITIONS[task["status"]])
    return jsonify(tasks=tasks, summary=summarize(tasks), priorities=list(PRIORITIES))


@task_bp.route("/properties/<int:property_id>/tasks", methods=["POST"])
@require_user
def create_task(property_id):
    # the flow that crosses the seam: a task may only be added to a property the user owns
    try:
        found = fetch_property(property_id, request.headers["Authorization"])
    except PropertyServiceUnavailable:
        return jsonify(error="Property service unavailable, try adding the task again later"), 503
    if found is None:
        return jsonify(error="Property not found"), 404

    body = request.get_json(silent=True) or {}
    connection = Database.connect()
    try:
        task_id = add_task(
            connection,
            g.user_id,
            property_id,
            body.get("task_name"),
            body.get("description"),
            body.get("priority", "normal"),
        )
        created = get_task(connection, g.user_id, property_id, task_id)
    except ValueError as error:
        return jsonify(error=str(error)), 400
    finally:
        connection.close()

    return jsonify(created), 201


@task_bp.route("/properties/<int:property_id>/tasks/<int:task_id>", methods=["PATCH"])
@require_user
def change_status(property_id, task_id):
    body = request.get_json(silent=True) or {}
    connection = Database.connect()
    try:
        update_status(connection, g.user_id, property_id, task_id, body.get("status"))
    except LookupError:
        return jsonify(error="Task not found"), 404
    except ValueError as error:
        return jsonify(error=str(error)), 400
    finally:
        connection.close()

    return "", 204


@task_bp.route("/properties/<int:property_id>/tasks/<int:task_id>", methods=["DELETE"])
@require_user
def remove_task(property_id, task_id):
    connection = Database.connect()
    deleted = delete_task(connection, g.user_id, property_id, task_id)
    connection.close()

    if not deleted:
        return jsonify(error="Task not found"), 404
    return "", 204
