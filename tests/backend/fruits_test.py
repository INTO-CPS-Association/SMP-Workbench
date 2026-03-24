from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.backend.main import app

client = TestClient(app)


def test_get_fruits():
    response = client.get("/fruits")
    assert response.status_code == 200
    assert response.json() == {"fruits": []}