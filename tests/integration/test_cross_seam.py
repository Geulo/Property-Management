# Integration test across the seam, against the real compose stack (not stubs):
#   docker compose up --build -d   then   python -m pytest tests/integration
# It signs up through property, adds a task through tasks (which calls property over HTTP to
# check the property), then stops property and checks tasks fails in its designed way.
import os
import subprocess
import time

import pytest
import requests

PROPERTY = os.environ.get("PROPERTY_BASE_URL", "http://localhost:8001")
TASKS = os.environ.get("TASKS_BASE_URL", "http://localhost:8002")


def wait_until_healthy(base_url, timeout_s=180):
    # SQL Server and the migrations take a while on the first start
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if requests.get(f"{base_url}/health", timeout=2).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(3)
    pytest.fail(f"{base_url}/health never returned 200")


def compose(*args):
    subprocess.run(["docker", "compose", *args], check=True)


@pytest.fixture(scope="module")
def auth():
    wait_until_healthy(PROPERTY)
    wait_until_healthy(TASKS)
    email = f"it-{int(time.time())}@example.com"
    requests.post(f"{PROPERTY}/signup", json={"username": "it", "email": email, "password": "password123"}, timeout=5)
    token = requests.post(f"{PROPERTY}/login", json={"email": email, "password": "password123"}, timeout=5).json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def property_id(auth):
    response = requests.post(f"{PROPERTY}/properties", json={"property_name": "Canal House", "address": "Street 1"}, headers=auth, timeout=5)
    assert response.status_code == 201
    return response.json()["property_id"]


def test_task_on_own_property_crosses_the_seam(auth, property_id):
    response = requests.post(f"{TASKS}/properties/{property_id}/tasks", json={"task_name": "Fix boiler"}, headers=auth, timeout=10)
    assert response.status_code == 201
    listed = requests.get(f"{TASKS}/properties/{property_id}/tasks", headers=auth, timeout=5).json()
    assert [task["task_name"] for task in listed["tasks"]] == ["Fix boiler"]


def test_task_on_unknown_property_is_refused_by_property(auth):
    response = requests.post(f"{TASKS}/properties/999999/tasks", json={"task_name": "Fix tap"}, headers=auth, timeout=10)
    assert response.status_code == 404


def test_property_down_is_handled(auth, property_id):
    compose("stop", "property")
    try:
        started = time.time()
        response = requests.post(f"{TASKS}/properties/{property_id}/tasks", json={"task_name": "Fix tap"}, headers=auth, timeout=10)
        assert response.status_code == 503
        assert "unavailable" in response.json()["error"]
        assert time.time() - started < 5  # bounded by PROPERTY_TIMEOUT_S, never a hung request

        # tasks keeps serving its own domain and reports only its own health
        assert requests.get(f"{TASKS}/properties/{property_id}/tasks", headers=auth, timeout=5).status_code == 200
        assert requests.get(f"{TASKS}/health", timeout=5).status_code == 200
    finally:
        compose("start", "property")
