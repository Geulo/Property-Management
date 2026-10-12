from flask import Blueprint, abort, redirect, render_template, request, session

from src.database import Database

# The ONLY import from the property domain. This is the seam: if tasks becomes its
# own service, get_property() turns into an HTTP call to the property service.
from src.property import get_property

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


# ---- logic (no Flask, takes a connection so it can be unit tested) ----

def add_task(connection, property_id, task_name, description="", priority="normal"):
    task_name = (task_name or "").strip()
    description = (description or "").strip()

    if not task_name:
        raise ValueError("Task name is required")
    if len(task_name) > MAX_TASK_NAME_LENGTH:
        raise ValueError(f"Task name must be at most {MAX_TASK_NAME_LENGTH} characters")
    if priority not in PRIORITIES:
        raise ValueError(f"Priority must be one of {', '.join(PRIORITIES)}")

    cursor = connection.execute(
        "INSERT INTO tasks (task_name, description, priority, property_id) VALUES (?, ?, ?, ?)",
        (task_name, description, priority, property_id),
    )
    connection.commit()
    return cursor.lastrowid


def list_tasks(connection, property_id):
    # open tasks first, then urgent before normal before low, newest first
    return connection.execute(
        """
        SELECT * FROM tasks WHERE property_id = ?
        ORDER BY
            CASE status WHEN 'done' THEN 1 ELSE 0 END,
            CASE priority WHEN 'urgent' THEN 0 WHEN 'normal' THEN 1 ELSE 2 END,
            task_id DESC
        """,
        (property_id,),
    ).fetchall()


def get_task(connection, task_id, property_id):
    return connection.execute(
        "SELECT * FROM tasks WHERE task_id = ? AND property_id = ?", (task_id, property_id)
    ).fetchone()


def can_transition(current_status, new_status):
    return new_status in ALLOWED_TRANSITIONS.get(current_status, ())


def update_status(connection, task_id, property_id, new_status):
    if new_status not in STATUSES:
        raise ValueError(f"Status must be one of {', '.join(STATUSES)}")

    task = get_task(connection, task_id, property_id)
    if task is None:
        raise LookupError("Task not found")
    if not can_transition(task["status"], new_status):
        raise ValueError(f"Cannot move task from {task['status']} to {new_status}")

    connection.execute(
        "UPDATE tasks SET status = ? WHERE task_id = ?", (new_status, task_id)
    )
    connection.commit()


def delete_task(connection, task_id, property_id):
    cursor = connection.execute(
        "DELETE FROM tasks WHERE task_id = ? AND property_id = ?", (task_id, property_id)
    )
    connection.commit()
    return cursor.rowcount == 1


def summarize(tasks):
    # pure function: counts per status + open urgent tasks, shown on the property page
    summary = {status: 0 for status in STATUSES}
    summary["urgent_open"] = 0
    for task in tasks:
        summary[task["status"]] += 1
        if task["priority"] == "urgent" and task["status"] != "done":
            summary["urgent_open"] += 1
    return summary


# ---- routes ----

@task_bp.before_request
def require_login():
    if "user_id" not in session:
        return redirect("/login")


def load_owned_property(connection, property_id):
    found = get_property(connection, property_id, session["user_id"])
    if found is None:
        connection.close()
        abort(404)
    return found


@task_bp.route("/properties/<int:property_id>")
def property_tasks(property_id, error=None):
    connection = Database.connect_sqlite()
    found = load_owned_property(connection, property_id)
    tasks = list_tasks(connection, property_id)
    connection.close()
    return render_template(
        "property.html",
        property=found,
        tasks=tasks,
        summary=summarize(tasks),
        transitions=ALLOWED_TRANSITIONS,
        priorities=PRIORITIES,
        error=error,
    )


@task_bp.route("/properties/<int:property_id>/tasks", methods=["POST"])
def create_task(property_id):
    connection = Database.connect_sqlite()
    load_owned_property(connection, property_id)
    try:
        add_task(
            connection,
            property_id,
            request.form.get("task_name"),
            request.form.get("description"),
            request.form.get("priority", "normal"),
        )
    except ValueError as error:
        connection.close()
        return property_tasks(property_id, error=str(error))

    connection.close()
    return redirect(f"/properties/{property_id}")


@task_bp.route("/properties/<int:property_id>/tasks/<int:task_id>/status", methods=["POST"])
def change_status(property_id, task_id):
    connection = Database.connect_sqlite()
    load_owned_property(connection, property_id)
    try:
        update_status(connection, task_id, property_id, request.form.get("status"))
    except LookupError:
        connection.close()
        abort(404)
    except ValueError as error:
        connection.close()
        return property_tasks(property_id, error=str(error))

    connection.close()
    return redirect(f"/properties/{property_id}")


@task_bp.route("/properties/<int:property_id>/tasks/<int:task_id>/delete", methods=["POST"])
def remove_task(property_id, task_id):
    connection = Database.connect_sqlite()
    load_owned_property(connection, property_id)
    delete_task(connection, task_id, property_id)
    connection.close()
    return redirect(f"/properties/{property_id}")
