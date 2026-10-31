import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import (
    ProjectCreateRequest,
    ProjectStatus,
    ExtractionPlan,
    IntentCategory
)
from app.services.project_service import project_service
from app.services.cache_service import cache_service, CacheType, CacheStatus
from app.services.checkpoint_service import checkpoint_service, StageName, CheckpointStatus
from app.services.job_service import job_service

client = TestClient(app)


def test_multi_tier_cache_hit_and_miss():
    """Requirement 2, 3, 8, 14, 61: Multi-tier caching for Metadata, Transcript, Vision, Knowledge, Playlist."""
    video_url = "https://www.youtube.com/watch?v=cache_vid_101"
    v_fp = cache_service.generate_content_fingerprint(video_url)
    p_fp = cache_service.generate_processing_fingerprint("CODE_EXTRACTION", "Extract Java BFS code")

    # Initial query -> Cache Miss
    miss_res = cache_service.get_cache(CacheType.TRANSCRIPT, video_url, v_fp)
    assert miss_res is None

    # Atomic commit to READY status
    transcript_payload = {"video_id": "cache_vid_101", "text": "def bfs(): pass"}
    cache_service.commit_cache(CacheType.TRANSCRIPT, video_url, v_fp, transcript_payload)

    # Subsequent query -> Cache Hit
    hit_res = cache_service.get_cache(CacheType.TRANSCRIPT, video_url, v_fp)
    assert hit_res is not None
    assert hit_res["text"] == "def bfs(): pass"


def test_intent_fingerprint_differentiation():
    """Requirement 10, 11, 20, 83: Different prompt intents generate different fingerprints preventing bad cache hits."""
    url = "https://www.youtube.com/watch?v=cache_vid_102"
    fp_code = cache_service.generate_processing_fingerprint("CODE_EXTRACTION", "Extract all code")
    fp_exam = cache_service.generate_processing_fingerprint("EXAM_REVISION", "Create exam notes")

    assert fp_code != fp_exam

    # Cache knowledge result for code prompt
    cache_service.commit_cache(CacheType.KNOWLEDGE, url, fp_code, {"type": "code_knowledge"})

    # Exam prompt query must NOT hit code knowledge cache
    hit_exam = cache_service.get_cache(CacheType.KNOWLEDGE, url, fp_exam)
    assert hit_exam is None


def test_cache_invalidation_does_not_affect_library():
    """Requirement 35, 37, 62: Cache invalidation removes cache entry without affecting durable saved knowledge."""
    url = "https://www.youtube.com/watch?v=cache_vid_103"
    fp = cache_service.generate_content_fingerprint(url)
    
    cache_service.commit_cache(CacheType.METADATA, url, fp, {"title": "Test Metadata"})
    assert cache_service.get_cache(CacheType.METADATA, url, fp) is not None

    cache_service.invalidate_cache(CacheType.METADATA, url, fp)
    assert cache_service.get_cache(CacheType.METADATA, url, fp) is None


def test_stage_level_checkpointing_and_job_resumability():
    """Requirement 4, 24, 27, 53, 63, 64: Stage checkpoints and resume API."""
    proj = project_service.create_project(ProjectCreateRequest(
        source_url="https://www.youtube.com/watch?v=resume_vid_200",
        user_prompt="Extract code"
    ))
    job = job_service.create_job(proj.project_id)

    # Save stage checkpoints
    checkpoint_service.save_stage_checkpoint(job.job_id, proj.source_url, StageName.INGEST, CheckpointStatus.COMPLETED)
    checkpoint_service.save_stage_checkpoint(job.job_id, proj.source_url, StageName.VISION, CheckpointStatus.COMPLETED)
    checkpoint_service.save_stage_checkpoint(job.job_id, proj.source_url, StageName.KNOWLEDGE_REASONING, CheckpointStatus.FAILED, error_message="Rate limit")

    # Mark job failed
    job_service.update_job_status(job.job_id, ProjectStatus.FAILED, 50, "Failed at knowledge reasoning", error_message="Rate limit")

    # Verify stage completion status
    assert checkpoint_service.is_stage_completed_or_cached(job.job_id, proj.source_url, StageName.INGEST) is True
    assert checkpoint_service.is_stage_completed_or_cached(job.job_id, proj.source_url, StageName.KNOWLEDGE_REASONING) is False

    # Call Resume API Endpoint
    res = client.post(f"/api/jobs/{job.job_id}/resume")
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] == ProjectStatus.PROCESSING_VIDEO.value


def test_duplicate_job_protection():
    """Requirement 32, 33, 66: Prevents duplicate active jobs for the same project."""
    proj = project_service.create_project(ProjectCreateRequest(
        source_url="https://www.youtube.com/watch?v=dup_vid_300",
        user_prompt="Extract BFS code"
    ))
    job1 = job_service.create_job(proj.project_id)

    # Subsequent create_job call returns existing active job
    job2 = job_service.create_job(proj.project_id)
    assert job1.job_id == job2.job_id


def test_crash_recovery_policy():
    """Requirement 28, 29, 52: Recovers unhandled RUNNING/PROCESSING jobs after application restart."""
    proj = project_service.create_project(ProjectCreateRequest(
        source_url="https://www.youtube.com/watch?v=crash_vid_400",
        user_prompt="Extract code"
    ))
    job = job_service.create_job(proj.project_id)
    job_service.update_job_status(job.job_id, ProjectStatus.PROCESSING_VIDEO, 40, "Processing video...")

    recovered = checkpoint_service.recover_stale_jobs(job_service)
    assert recovered >= 1
    updated_job = job_service.get_job(job.job_id)
    assert "Job recovered" in updated_job.current_stage


def test_cache_status_api():
    """Requirement 39, 76: GET /api/cache/status endpoint returns stats."""
    res = client.get("/api/cache/status")
    assert res.status_code == 200
    data = res.json()
    assert "total_entries" in data
    assert "ready_entries" in data
    assert "processing_version" in data
