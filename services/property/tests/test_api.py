# Smoke tests through the Flask test client: the JSON routes and the login token.
# Business rules are tested in the other files; these only check the wiring works.
import pytest

from app import create_app
from conftest import TEST_DATABASE_URL


@pytest.fixture
def client(connection, monkeypatch):
    # `connection` empties the test database (or skips without one)
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    monkeypatch.setenv("SECRET_KEY", "test-key")
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def log_in(client):
    client.post("/signup", json={"username": "ruben", "email": "r@example.com", "password": "password123"})
    token = client.post("/login", json={"email": "r@example.com", "password": "password123"}).get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["db"] == "ok"


def test_routes_require_a_token(client):
    assert client.get("/properties").status_code == 401
    assert client.get("/properties", headers={"Authorization": "Bearer forged"}).status_code == 401


def test_bad_login_and_signup(client):
    assert client.post("/login", json={"email": "x@example.com", "password": "nope"}).status_code == 401
    response = client.post("/signup", json={"username": "a", "email": "a@example.com", "password": "short"})
    assert response.status_code == 400
    assert "at least 8" in response.get_json()["error"]


def test_property_flow(client):
    headers = log_in(client)

    created = client.post("/properties", json={"property_name": "Canal House", "address": "Street 1"}, headers=headers)
    assert created.status_code == 201
    property_id = created.get_json()["property_id"]
    assert client.post("/properties", json={"property_name": ""}, headers=headers).status_code == 400

    assert client.get("/properties", headers=headers).get_json()["properties"][0]["property_name"] == "Canal House"
    assert client.get(f"/properties/{property_id}", headers=headers).status_code == 200

    assert client.delete(f"/properties/{property_id}", headers=headers).status_code == 204
    assert client.get(f"/properties/{property_id}", headers=headers).status_code == 404
