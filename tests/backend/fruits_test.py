from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_app_root_returns_404_for_unknown_routes():
    response = client.get("/unknown-route")
    assert response.status_code == 404
