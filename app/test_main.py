from main import app


def test_health_returns_ok():
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_index_returns_message_and_version():
    response = app.test_client().get("/")
    body = response.get_json()
    assert response.status_code == 200
    assert "message" in body
    assert "version" in body