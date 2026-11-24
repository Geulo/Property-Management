# Smoke tests through the Flask test client. The property service is replaced by a stub
# (fetch_property is patched), so these check how tasks behaves for each answer it could get.
import pytest

import src.task
from app import create_app
from conftest import TEST_DATABASE_URL
from src.auth import make_token
from src.database import Database
from src.property_client import PropertyServiceUnavailable


@pytest.fixture
def client(connection, monkeypatch):
    # `connection` empties the test database (or skips without one)
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("SECRET_KEY", "test-key")
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def headers():
    return {"Authorization": f"Bearer {make_token('test-key', 1)}"}


def property_answers(monkeypatch, answer):
    def fake_fetch(property_id, authorization):
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(src.task, "fetch_property", fake_fetch)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "db": "ok", "version": "dev"}


def test_routes_require_a_token(client):
    assert client.get("/properties/10/tasks").status_code == 401
    assert client.get("/properties/10/tasks", headers={"Authorization": "Bearer forged"}).status_code == 401


def test_task_flow(client, headers, monkeypatch):
    property_answers(monkeypatch, {"property_id": 10})

    created = client.post("/properties/10/tasks", json={"task_name": "Fix boiler", "priority": "urgent"}, headers=headers)
    assert created.status_code == 201
    task_id = created.get_json()["task_id"]
    assert client.post("/properties/10/tasks", json={"task_name": ""}, headers=headers).status_code == 400

    body = client.get("/properties/10/tasks", headers=headers).get_json()
    assert body["summary"]["urgent_open"] == 1
    assert body["tasks"][0]["next_statuses"] == ["in_progress", "done"]

    assert client.patch(f"/properties/10/tasks/{task_id}", json={"status": "done"}, headers=headers).status_code == 204
    assert client.patch(f"/properties/10/tasks/{task_id}", json={"status": "in_progress"}, headers=headers).status_code == 400
    assert client.patch("/properties/10/tasks/999", json={"status": "done"}, headers=headers).status_code == 404

    assert client.delete(f"/properties/10/tasks/{task_id}", headers=headers).status_code == 204
    assert client.delete(f"/properties/10/tasks/{task_id}", headers=headers).status_code == 404


def test_unknown_property_is_404(client, headers, monkeypatch):
    property_answers(monkeypatch, None)
    assert client.post("/properties/10/tasks", json={"task_name": "Fix tap"}, headers=headers).status_code == 404


def test_property_service_down(client, headers, monkeypatch):
    property_answers(monkeypatch, PropertyServiceUnavailable("timed out"))
    response = client.post("/properties/10/tasks", json={"task_name": "Fix tap"}, headers=headers)
    assert response.status_code == 503
    assert "unavailable" in response.get_json()["error"]
    # its own domain keeps working: listing does not call property at all
    assert client.get("/properties/10/tasks", headers=headers).status_code == 200


def test_cors_only_for_the_ui_origin(client):
    allowed = client.get("/health", headers={"Origin": "http://localhost:8080"})
    assert allowed.headers["Access-Control-Allow-Origin"] == "http://localhost:8080"
    other = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "Access-Control-Allow-Origin" not in other.headers


def test_delete_all_tasks_of_a_property(client, headers, monkeypatch):
    property_answers(monkeypatch, {"property_id": 7})
    client.post("/properties/7/tasks", json={"task_name": "Fix tap"}, headers=headers)
    assert client.delete("/properties/7/tasks", headers=headers).status_code == 204
    assert client.get("/properties/7/tasks", headers=headers).get_json()["tasks"] == []
    assert client.delete("/properties/7/tasks").status_code == 401


def test_health_is_503_without_its_database(client, monkeypatch):
    def unreachable(*args, **kwargs):
        raise ConnectionError("database down")

    monkeypatch.setattr(Database, "connect", unreachable)
    response = client.get("/health")
    assert response.status_code == 503
    assert response.get_json()["db"] == "error"
