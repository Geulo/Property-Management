import sqlite3

import pytest

from src.property import add_property
from src.task import (
    add_task,
    can_transition,
    delete_task,
    get_task,
    list_tasks,
    summarize,
    update_status,
)


@pytest.fixture
def property_id(connection, user_id):
    return add_property(connection, user_id, "Canal House", "Street 1")


def test_new_task_defaults(connection, property_id):
    task_id = add_task(connection, property_id, "Fix leaking tap")
    task = get_task(connection, task_id, property_id)
    assert task["status"] == "pending"
    assert task["priority"] == "normal"


@pytest.mark.parametrize("name", ["", "   ", None])
def test_task_name_required(connection, property_id, name):
    with pytest.raises(ValueError, match="required"):
        add_task(connection, property_id, name)


def test_task_name_too_long(connection, property_id):
    with pytest.raises(ValueError, match="at most"):
        add_task(connection, property_id, "x" * 81)


def test_invalid_priority_rejected(connection, property_id):
    with pytest.raises(ValueError, match="Priority"):
        add_task(connection, property_id, "Fix tap", priority="whenever")


def test_task_needs_existing_property(connection):
    # foreign key: a task can't point at a property that doesn't exist
    with pytest.raises(sqlite3.IntegrityError):
        add_task(connection, 999, "Fix tap")


def test_list_orders_open_urgent_first(connection, property_id):
    done_id = add_task(connection, property_id, "Paint fence", priority="urgent")
    update_status(connection, done_id, property_id, "done")
    add_task(connection, property_id, "Clean gutters", priority="low")
    add_task(connection, property_id, "Broken heating", priority="urgent")

    names = [t["task_name"] for t in list_tasks(connection, property_id)]
    assert names == ["Broken heating", "Clean gutters", "Paint fence"]


@pytest.mark.parametrize("current, new, allowed", [
    ("pending", "in_progress", True),
    ("pending", "done", True),
    ("in_progress", "done", True),
    ("in_progress", "pending", True),
    ("done", "pending", True),
    ("done", "in_progress", False),
    ("pending", "pending", False),
    ("unknown", "done", False),
])
def test_can_transition(current, new, allowed):
    assert can_transition(current, new) is allowed


def test_update_status(connection, property_id):
    task_id = add_task(connection, property_id, "Fix tap")
    update_status(connection, task_id, property_id, "in_progress")
    assert get_task(connection, task_id, property_id)["status"] == "in_progress"


def test_update_status_rejects_invalid_transition(connection, property_id):
    task_id = add_task(connection, property_id, "Fix tap")
    update_status(connection, task_id, property_id, "done")
    with pytest.raises(ValueError, match="Cannot move"):
        update_status(connection, task_id, property_id, "in_progress")


def test_update_status_rejects_unknown_status(connection, property_id):
    task_id = add_task(connection, property_id, "Fix tap")
    with pytest.raises(ValueError, match="Status must be"):
        update_status(connection, task_id, property_id, "archived")


def test_update_status_task_must_belong_to_property(connection, user_id, property_id):
    other_property = add_property(connection, user_id, "Other", "Street 2")
    task_id = add_task(connection, property_id, "Fix tap")
    with pytest.raises(LookupError):
        update_status(connection, task_id, other_property, "done")


def test_delete_task(connection, property_id):
    task_id = add_task(connection, property_id, "Fix tap")
    assert delete_task(connection, task_id, property_id) is True
    assert get_task(connection, task_id, property_id) is None


def test_delete_task_wrong_property(connection, user_id, property_id):
    other_property = add_property(connection, user_id, "Other", "Street 2")
    task_id = add_task(connection, property_id, "Fix tap")
    assert delete_task(connection, task_id, other_property) is False


def test_summarize():
    tasks = [
        {"status": "pending", "priority": "urgent"},
        {"status": "in_progress", "priority": "normal"},
        {"status": "done", "priority": "urgent"},
        {"status": "done", "priority": "low"},
    ]
    assert summarize(tasks) == {"pending": 1, "in_progress": 1, "done": 2, "urgent_open": 1}


def test_summarize_empty():
    assert summarize([]) == {"pending": 0, "in_progress": 0, "done": 0, "urgent_open": 0}
