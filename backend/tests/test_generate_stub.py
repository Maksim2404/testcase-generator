from fastapi.testclient import TestClient
from backend.main import app

def test_generate_stub():
    client = TestClient(app)
    payload = {
        "app": "APP1",
        "area": "Login > UserName field",
        "suite": "Regression",
        "priority": "P2",
        "notes": "As a user I can input/type a UserName value into a field"
    }
    r = client.post("/api/generate?mode=stub", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "markdown" in data
    assert data["markdown"].startswith("---")  # YAML front-matter