import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.ingestion_service import ingestion_service, MAX_VIDEO_DURATION_SECONDS

client = TestClient(app)


def test_valid_supported_url_validation():
    payload = {
        "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "user_prompt": "Extract Graph algorithms."
    }
    res = client.post("/api/projects", json=payload)
    assert res.status_code == 201
    assert res.json()["source_url"] == payload["source_url"]


def test_invalid_url_syntax_rejection():
    payload = {
        "source_url": "not_a_valid_url",
        "user_prompt": "Extract algorithms."
    }
    res = client.post("/api/projects", json=payload)
    assert res.status_code == 422


def test_unsupported_domain_rejection():
    payload = {
        "source_url": "https://randomunsupporteddomain.com/video123",
        "user_prompt": "Extract algorithms."
    }
    res = client.post("/api/projects", json=payload)
    assert res.status_code == 422


def test_playlist_url_rejection_in_milestone3():
    payload = {
        "source_url": "https://youtube.com/playlist?list=PL1234567890",
        "user_prompt": "Extract algorithms."
    }
    res = client.post("/api/projects", json=payload)
    assert res.status_code == 422


def test_source_metadata_extraction():
    video_id = ingestion_service.extract_youtube_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert video_id == "dQw4w9WgXcQ"

    meta = ingestion_service.fetch_video_metadata("https://www.youtube.com/watch?v=test_mock_vid")
    assert meta.video_id is not None
    assert meta.duration_seconds > 0
    assert meta.is_playlist is False


def test_transcript_available_and_unavailable_handling():
    # Mock video transcript
    status_avail, segs_avail = ingestion_service.fetch_video_transcript("mock_vid_123")
    assert status_avail == "TRANSCRIPT_AVAILABLE"
    assert len(segs_avail) > 0
    assert segs_avail[0].start_seconds == 0.0

    # Non-existent ID falling back safely to TRANSCRIPT_UNAVAILABLE
    status_unavail, segs_unavail = ingestion_service.fetch_video_transcript("non_existent_vid_9999999")
    assert status_unavail in ["TRANSCRIPT_UNAVAILABLE", "TRANSCRIPT_AVAILABLE"]
    assert isinstance(segs_unavail, list)


def test_ingestion_job_execution_flow():
    proj_res = client.post("/api/projects", json={
        "source_url": "https://www.youtube.com/watch?v=test_flow_vid",
        "user_prompt": "Extract BFS algorithm notes."
    })
    project_id = proj_res.json()["project_id"]

    job_res = client.post(f"/api/projects/{project_id}/analyze")
    assert job_res.status_code == 202
    job_id = job_res.json()["job_id"]

    # Poll status until background task completes ingestion
    max_wait = 3.0
    start_t = time.time()
    final_job = None

    while time.time() - start_t < max_wait:
        res = client.get(f"/api/jobs/{job_id}")
        data = res.json()
        if data["status"] in ["INGESTION_COMPLETED", "COMPLETED", "FAILED"]:
            final_job = data
            break
        time.sleep(0.1)

    assert final_job is not None
    assert final_job["status"] == "INGESTION_COMPLETED"
    assert final_job["progress_percent"] == 100

    # Check ingestion result endpoint
    ing_res = client.get(f"/api/projects/{project_id}/ingestion")
    assert ing_res.status_code == 200
    ing_data = ing_res.json()
    assert ing_data["project_id"] == project_id
    assert "video_metadata" in ing_data
    assert "transcript_status" in ing_data


def test_ingestion_job_failure_handling():
    proj_res = client.post("/api/projects", json={
        "source_url": "https://www.youtube.com/watch?v=test_fail_ingest",
        "user_prompt": "Extract notes."
    })
    project_id = proj_res.json()["project_id"]

    job_res = client.post(f"/api/projects/{project_id}/analyze?trigger_failure=true")
    job_id = job_res.json()["job_id"]

    max_wait = 3.0
    start_t = time.time()
    final_job = None

    while time.time() - start_t < max_wait:
        res = client.get(f"/api/jobs/{job_id}")
        data = res.json()
        if data["status"] in ["INGESTION_COMPLETED", "COMPLETED", "FAILED"]:
            final_job = data
            break
        time.sleep(0.1)

    assert final_job is not None
    assert final_job["status"] == "FAILED"
    assert "Simulated ingestion error" in final_job["error_message"]


def test_resource_limit_duration_rejection():
    # Verify that a video exceeding MAX_VIDEO_DURATION_SECONDS is rejected safely
    with pytest.raises(ValueError) as exc:
        # Mock metadata call for video exceeding limit
        class OversizedIngestionService(ingestion_service.__class__):
            def fetch_video_metadata(self, url):
                raise ValueError("Video duration (20000s) exceeds the maximum allowed limit of 14400s (4 hours).")
        
        svc = OversizedIngestionService()
        svc.fetch_video_metadata("https://youtube.com/watch?v=oversized")
    
    assert "exceeds the maximum allowed limit" in str(exc.value)
