import pytest

from src.task import (
    add_task,
    can_transition,
    delete_task,
    get_task,
    list_tasks,
    summarize,
    update_status,
)


def test_new_task_defaults(connection, user_id, property_id):
    task_id = add_task(connection, user_id, property_id, "Fix leaking tap")
    task = get_task(connection, user_id, property_id, task_id)
    assert task["status"] == "pending"
    assert task["priority"] == "normal"


@pytest.mark.parametrize("name", ["", "   ", None])
def test_task_name_required(user_id, property_id, name):
    with pytest.raises(ValueError, match="required"):
        add_task(None, user_id, property_id, name)


def test_task_name_too_long(user_id, property_id):
    with pytest.raises(ValueError, match="at most"):
        add_task(None, user_id, property_id, "x" * 81)


def test_invalid_priority_rejected(user_id, property_id):
    with pytest.raises(ValueError, match="Priority"):
        add_task(None, user_id, property_id, "Fix tap", priority="whenever")


def test_users_only_see_their_own_tasks(connection, user_id, property_id):
    task_id = add_task(connection, user_id, property_id, "Fix tap")
    assert list_tasks(connection, user_id + 1, property_id) == []
    assert get_task(connection, user_id + 1, property_id, task_id) is None


def test_list_orders_open_urgent_first(connection, user_id, property_id):
    done_id = add_task(connection, user_id, property_id, "Paint fence", priority="urgent")
    update_status(connection, user_id, property_id, done_id, "done")
    add_task(connection, user_id, property_id, "Clean gutters", priority="low")
    add_task(connection, user_id, property_id, "Broken heating", priority="urgent")

    names = [t["task_name"] for t in list_tasks(connection, user_id, property_id)]
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


def test_update_status(connection, user_id, property_id):
    task_id = add_task(connection, user_id, property_id, "Fix tap")
    update_status(connection, user_id, property_id, task_id, "in_progress")
    assert get_task(connection, user_id, property_id, task_id)["status"] == "in_progress"


def test_update_status_rejects_invalid_transition(connection, user_id, property_id):
    task_id = add_task(connection, user_id, property_id, "Fix tap")
    update_status(connection, user_id, property_id, task_id, "done")
    with pytest.raises(ValueError, match="Cannot move"):
        update_status(connection, user_id, property_id, task_id, "in_progress")


def test_update_status_rejects_unknown_status(connection, user_id, property_id):
    task_id = add_task(connection, user_id, property_id, "Fix tap")
    with pytest.raises(ValueError, match="Status must be"):
        update_status(connection, user_id, property_id, task_id, "archived")


def test_update_status_task_must_belong_to_property(connection, user_id, property_id):
    other_property = property_id + 1
    task_id = add_task(connection, user_id, property_id, "Fix tap")
    with pytest.raises(LookupError):
        update_status(connection, user_id, other_property, task_id, "done")


def test_delete_task(connection, user_id, property_id):
    task_id = add_task(connection, user_id, property_id, "Fix tap")
    assert delete_task(connection, user_id, property_id, task_id) is True
    assert get_task(connection, user_id, property_id, task_id) is None


def test_delete_task_wrong_property(connection, user_id, property_id):
    other_property = property_id + 1
    task_id = add_task(connection, user_id, property_id, "Fix tap")
    assert delete_task(connection, user_id, other_property, task_id) is False


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
