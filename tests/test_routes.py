# Smoke tests through the Flask test client: one happy path per feature domain.
# Business rules are tested in the other files; these only check the wiring works.
import pytest

from main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def sign_up_and_log_in(client):
    client.post("/signup", data={"username": "ruben", "email": "r@example.com", "password": "password123"})
    return client.post("/login", data={"email": "r@example.com", "password": "password123"})


def test_pages_require_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_signup_login_logout(client):
    assert client.get("/signup").status_code == 200
    assert client.get("/login").status_code == 200
    assert sign_up_and_log_in(client).headers["Location"].endswith("/")
    client.get("/logout")
    assert client.get("/").status_code == 302


def test_bad_login_and_signup_show_errors(client):
    assert b"Invalid email or password" in client.post("/login", data={"email": "x@example.com", "password": "nope"}).data
    assert b"at least 8" in client.post("/signup", data={"username": "a", "email": "a@example.com", "password": "short"}).data


def test_property_and_task_flow(client):
    sign_up_and_log_in(client)

    client.post("/properties", data={"property_name": "Canal House", "address": "Street 1"})
    assert b"Canal House" in client.get("/").data
    assert b"required" in client.post("/properties", data={"property_name": "", "address": ""}).data

    client.post("/properties/1/tasks", data={"task_name": "Fix boiler", "priority": "urgent"})
    page = client.get("/properties/1").data
    assert b"Fix boiler" in page
    assert b"1 urgent open" in page
    assert b"required" in client.post("/properties/1/tasks", data={"task_name": ""}).data

    client.post("/properties/1/tasks/1/status", data={"status": "done"})
    assert b"1 done" in client.get("/properties/1").data
    assert b"Cannot move" in client.post("/properties/1/tasks/1/status", data={"status": "in_progress"}).data
    assert client.post("/properties/1/tasks/99/status", data={"status": "done"}).status_code == 404

    client.post("/properties/1/tasks/1/delete")
    assert b"No tasks" in client.get("/properties/1").data

    client.post("/properties/1/delete")
    assert client.get("/properties/1").status_code == 404
    assert client.post("/properties/1/delete").status_code == 404
