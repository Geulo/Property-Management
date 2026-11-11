# The seam without a property service: requests.get is replaced by a stub, so these
# check how tasks reacts to each answer (or no answer) from property.
import pytest
import requests

from src.property_client import PropertyServiceUnavailable, fetch_property


class FakeResponse:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self.body = body

    def json(self):
        return self.body


def answer_with(monkeypatch, response=None, error=None):
    calls = []

    def fake_get(url, headers, timeout):
        calls.append({"url": url, "headers": headers, "timeout": timeout})
        if error:
            raise error
        return response

    monkeypatch.setattr(requests, "get", fake_get)
    return calls


def test_found_property_is_returned_and_token_passed_on(monkeypatch):
    monkeypatch.setenv("PROPERTY_URL", "http://property:8000/")
    calls = answer_with(monkeypatch, FakeResponse(200, {"property_id": 5}))
    assert fetch_property(5, "Bearer abc") == {"property_id": 5}
    assert calls[0]["url"] == "http://property:8000/properties/5"
    assert calls[0]["headers"] == {"Authorization": "Bearer abc"}


def test_every_call_has_a_timeout(monkeypatch):
    monkeypatch.setenv("PROPERTY_TIMEOUT_S", "2")
    calls = answer_with(monkeypatch, FakeResponse(200, {}))
    fetch_property(5, "Bearer abc")
    assert calls[0]["timeout"] == 2.0


def test_unknown_property_is_none(monkeypatch):
    answer_with(monkeypatch, FakeResponse(404))
    assert fetch_property(5, "Bearer abc") is None


@pytest.mark.parametrize("error", [requests.Timeout(), requests.ConnectionError()])
def test_down_or_slow_service_raises_unavailable(monkeypatch, error):
    answer_with(monkeypatch, error=error)
    with pytest.raises(PropertyServiceUnavailable):
        fetch_property(5, "Bearer abc")


def test_server_error_raises_unavailable(monkeypatch):
    answer_with(monkeypatch, FakeResponse(500))
    with pytest.raises(PropertyServiceUnavailable):
        fetch_property(5, "Bearer abc")
