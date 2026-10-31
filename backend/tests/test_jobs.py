import time
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_analyze_project_success():
    # 1. Create a project
    proj_res = client.post("/api/projects", json={
        "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "user_prompt": "Extract Graph algorithms and code."
    })
    assert proj_res.status_code == 201
    project_id = proj_res.json()["project_id"]

    # 2. Trigger analysis job
    job_res = client.post(f"/api/projects/{project_id}/analyze")
    assert job_res.status_code == 202
    job_data = job_res.json()
    assert "job_id" in job_data
    assert job_data["project_id"] == project_id
    assert job_data["status"] == "PENDING"

    # 3. Retrieve job status
    job_id = job_data["job_id"]
    status_res = client.get(f"/api/jobs/{job_id}")
    assert status_res.status_code == 200
    assert status_res.json()["job_id"] == job_id


def test_analyze_nonexistent_project():
    job_res = client.post("/api/projects/proj_nonexistent_999/analyze")
    assert job_res.status_code == 404


def test_get_nonexistent_job():
    status_res = client.get("/api/jobs/job_nonexistent_999")
    assert status_res.status_code == 404


def test_job_execution_completion():
    # Create project & job
    proj_res = client.post("/api/projects", json={
        "source_url": "https://youtube.com/watch?v=test",
        "user_prompt": "Extract BFS algorithm notes."
    })
    project_id = proj_res.json()["project_id"]

    job_res = client.post(f"/api/projects/{project_id}/analyze")
    job_id = job_res.json()["job_id"]

    # Poll status until background task completes (simulated delay in service is fast)
    max_wait = 3.0
    start_t = time.time()
    final_status = None

    while time.time() - start_t < max_wait:
        res = client.get(f"/api/jobs/{job_id}")
        data = res.json()
        if data["status"] in ["COMPLETED", "FAILED"]:
            final_status = data
            break
        time.sleep(0.1)

    assert final_status is not None, "Job did not complete within timeout window."
    assert final_status["status"] == "COMPLETED"
    assert final_status["progress_percent"] == 100
    assert final_status["current_stage"] == "Knowledge artifact generated successfully!"


def test_job_execution_failure_handling():
    # Create project & job configured to fail
    proj_res = client.post("/api/projects", json={
        "source_url": "https://youtube.com/watch?v=test_fail",
        "user_prompt": "Extract revision notes."
    })
    project_id = proj_res.json()["project_id"]

    job_res = client.post(f"/api/projects/{project_id}/analyze?trigger_failure=true")
    job_id = job_res.json()["job_id"]

    max_wait = 3.0
    start_t = time.time()
    final_status = None

    while time.time() - start_t < max_wait:
        res = client.get(f"/api/jobs/{job_id}")
        data = res.json()
        if data["status"] in ["COMPLETED", "FAILED"]:
            final_status = data
            break
        time.sleep(0.1)

    assert final_status is not None
    assert final_status["status"] == "FAILED"
    assert "Simulated processing error" in final_status["error_message"]


def test_job_sse_stream_endpoint():
    proj_res = client.post("/api/projects", json={
        "source_url": "https://youtube.com/watch?v=sse_test",
        "user_prompt": "Extract revision notes."
    })
    project_id = proj_res.json()["project_id"]
    job_res = client.post(f"/api/projects/{project_id}/analyze")
    job_id = job_res.json()["job_id"]

    # Connect to stream
    with client.stream("GET", f"/api/jobs/{job_id}/stream") as stream:
        lines = []
        for line in stream.iter_lines():
            if line:
                lines.append(line)
            if len(lines) >= 2:
                break
        assert len(lines) > 0
        assert "data:" in lines[0]
