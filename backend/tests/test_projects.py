from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_project_success():
    payload = {
        "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "user_prompt": "Extract all algorithms, code, explanations, and complexity."
    }
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "project_id" in data
    assert data["source_url"] == payload["source_url"]
    assert data["user_prompt"] == payload["user_prompt"]
    assert data["status"] == "PENDING"

    # Test fetching created project
    project_id = data["project_id"]
    get_res = client.get(f"/api/projects/{project_id}")
    assert get_res.status_code == 200
    assert get_res.json()["project_id"] == project_id


def test_create_project_invalid_url():
    payload = {
        "source_url": "invalid-url-string",
        "user_prompt": "Extract revision notes."
    }
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 422  # Pydantic validation error


def test_create_project_short_prompt():
    payload = {
        "source_url": "https://youtube.com/watch?v=test",
        "user_prompt": "a"
    }
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 422  # Pydantic validation error for prompt min_length


def test_get_nonexistent_project():
    response = client.get("/api/projects/nonexistent_id_9999")
    assert response.status_code == 404
