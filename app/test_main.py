import json
import logging

import pytest

import main
from main import app


@pytest.fixture
def client():
    return app.test_client()


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_health_is_unhealthy_when_chaos_flag_is_set(client, monkeypatch):
    monkeypatch.setenv("CHAOS_UNHEALTHY", "1")
    response = client.get("/health")
    assert response.status_code == 503
    assert response.get_json() == {"status": "unhealthy"}


def test_index_returns_message_and_version(client):
    response = client.get("/")
    body = response.get_json()
    assert response.status_code == 200
    assert "message" in body
    assert "version" in body


def test_version_reports_version_and_uptime(client):
    response = client.get("/version")
    body = response.get_json()
    assert response.status_code == 200
    assert body["version"] == main.APP_VERSION
    assert body["uptime_seconds"] >= 0


def test_work_burns_cpu_for_requested_time(client):
    response = client.get("/work?ms=20")
    body = response.get_json()
    assert response.status_code == 200
    assert body["worked_ms"] == 20
    assert body["iterations"] > 0


def test_work_uses_default_duration(client):
    response = client.get("/work")
    assert response.status_code == 200
    assert response.get_json()["worked_ms"] == 100


@pytest.mark.parametrize("value", ["0", "-5", str(main.MAX_WORK_MS + 1), "abc", "1.5"])
def test_work_rejects_invalid_duration(client, value):
    response = client.get(f"/work?ms={value}")
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_unknown_path_returns_json_404(client):
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.get_json() == {"error": "not found"}


def test_wrong_method_returns_json_405(client):
    response = client.post("/health")
    assert response.status_code == 405
    assert response.get_json() == {"error": "method not allowed"}


def test_unhandled_error_returns_json_500(client, monkeypatch):
    def boom():
        raise RuntimeError("boom")

    monkeypatch.setitem(app.view_functions, "index", boom)
    app.config["PROPAGATE_EXCEPTIONS"] = False
    response = client.get("/")
    assert response.status_code == 500
    assert response.get_json() == {"error": "internal server error"}


def test_security_headers_are_set(client):
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Cache-Control"] == "no-store"


def test_requests_are_logged_as_json_but_health_is_not(client, caplog):
    main.logger.propagate = True  # let caplog see the records
    try:
        with caplog.at_level(logging.INFO, logger="finops"):
            client.get("/health")
            client.get("/version")
    finally:
        main.logger.propagate = False

    paths = [getattr(r, "fields", {}).get("path") for r in caplog.records]
    assert "/version" in paths
    assert "/health" not in paths

    line = main.JsonFormatter().format(caplog.records[-1])
    parsed = json.loads(line)
    assert parsed["message"] == "request"
    assert parsed["status"] == 200