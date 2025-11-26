from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add the backend directory to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from main import app

client = TestClient(app)

def test_read_main():
    response = client.get("/documents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_404_handler():
    response = client.get("/non-existent-route")
    assert response.status_code == 404

def test_cors_headers():
    response = client.options("/documents", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
