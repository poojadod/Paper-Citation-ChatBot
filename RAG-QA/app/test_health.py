"""A tiny test: does /health respond correctly?
Uses FastAPI's TestClient, which calls your endpoints in-process —
no server, no network needed."""
from fastapi.testclient import TestClient

from app.main import app          # import your FastAPI app

client = TestClient(app)          # a fake client that can call your endpoints


def done():
    response = client.get("/health")          # call GET /health
    assert response.status_code == 200        # HTTP success
    assert response.json() == {"status": "ok"}  # exact body we expect
