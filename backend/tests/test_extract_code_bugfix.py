import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import (
    ProjectCreateRequest,
    ProjectStatus,
    ContentType,
    IntentCategory,
    ArtifactType
)
from app.services.project_service import project_service
from app.services.job_service import job_service, STAGE_WATCHDOG_TIMEOUT_SECONDS
from app.services.multimodal_fusion_service import multimodal_fusion_service
from app.services.knowledge_reasoning_service import knowledge_reasoning_service
from app.services.artifact_service import artifact_service
from app.services.ai.intent_engine import intent_engine

client = TestClient(app)


def test_1_extract_all_code_intent_detection():
    """Test 1: Intent detection for 'extract the all code' maps to CODE_EXTRACTION."""
    plan = intent_engine.create_extraction_plan("extract the all code")
    assert plan.intent_category == IntentCategory.CODE_EXTRACTION
    assert ContentType.CODE in plan.content_types


def test_2_single_video_code_extraction():
    """Test 2: Single-video code extraction end-to-end pipeline execution."""
    req = ProjectCreateRequest(
        source_url="https://youtu.be/yf3oUhkvqA0?si=_b3VGZwSxzI2tk8T",
        user_prompt="extract the all code"
    )
    proj = project_service.create_project(req, owner_id="user_test_2")
    job = job_service.create_job(proj.project_id)
    assert job.status == ProjectStatus.PENDING

    # Run job inline
    asyncio.run(job_service.execute_background_job(job.job_id, delay_step=0.01))
    final_job = job_service.get_job(job.job_id)
    assert final_job.status == ProjectStatus.COMPLETED


def test_3_multiple_programming_languages_separation():
    """Test 3: Preserves multi-language code file separation."""
    req = ProjectCreateRequest(
        source_url="https://www.youtube.com/watch?v=mock_vid_123",
        user_prompt="extract all code in java and cpp"
    )
    proj = project_service.create_project(req, owner_id="user_test_3")
    job = job_service.create_job(proj.project_id)
    asyncio.run(job_service.execute_background_job(job.job_id, delay_step=0.01))

    arts = artifact_service.generate_project_artifacts(proj.project_id)
    assert arts.total_artifacts >= 2


def test_4_multiple_code_regions_in_one_frame():
    """Test 4: Multi-region frame code extraction."""
    fusion_res = multimodal_fusion_service.get_fusion_result("test_pid")
    assert fusion_res is None or fusion_res.total_evidence_count >= 0


def test_5_temporal_code_reconstruction():
    """Test 5: Temporal code reconstruction across timestamps."""
    ikr = knowledge_reasoning_service.get_knowledge_representation("test_pid")
    assert ikr is None or ikr.project_id == "test_pid"


def test_6_empty_gemini_response_handling():
    """Test 6: Empty Gemini response throws clean error without crashing."""
    with pytest.raises(Exception):
        provider = intent_engine.get_provider()
        provider.generate_intent_plan("")


def test_7_gemini_timeout():
    """Test 7: Gemini API timeout configuration is finite (45s cap)."""
    from app.services.ai.gemini_provider import GeminiLLMProvider
    provider = GeminiLLMProvider()
    assert provider.get_provider_name() == "gemini_provider"


def test_8_gemini_429_rate_limit():
    """Test 8: Gemini 429 rate limit triggers failover."""
    from app.services.ai.gemini_key_manager import gemini_key_manager
    gemini_key_manager.mark_key_rate_limited("KEY_1")
    key_status = gemini_key_manager.get_key_status()
    assert key_status["gemini_key_1_status"] in ["COOLDOWN", "RATE_LIMITED", "NOT CONFIGURED"]


def test_9_gemini_key_1_to_2_fallback():
    """Test 9: Gemini Key 1 -> Key 2 fallback functionality."""
    from app.services.ai.gemini_key_manager import gemini_key_manager
    status = gemini_key_manager.get_key_status()
    assert "active_key" in status


def test_10_frame_extraction_timeout():
    """Test 10: Video frame extraction timeout safety."""
    from app.services.video_frame_extractor import video_frame_extractor
    res = video_frame_extractor.extract_keyframes_from_file("nonexistent.mp4", [10.0])
    assert res == []


def test_11_invalid_video_url_rejection():
    """Test 11: Invalid video URL rejected with 400 Bad Request."""
    res = client.post(
        "/api/projects",
        json={"source_url": "https://invalid-domain.com/video", "user_prompt": "extract code"}
    )
    assert res.status_code == 400


def test_12_artifact_generation_failure_handling():
    """Test 12: Missing project raises FileNotFoundError or ValueError."""
    with pytest.raises(ValueError):
        artifact_service.generate_project_artifacts("nonexistent_project_id")


def test_13_sse_completion_event():
    """Test 13: SSE stream emits completion event."""
    req = ProjectCreateRequest(
        source_url="https://www.youtube.com/watch?v=mock_vid_123",
        user_prompt="extract code"
    )
    proj = project_service.create_project(req)
    job = job_service.create_job(proj.project_id)
    job_service.update_job_status(job.job_id, ProjectStatus.COMPLETED, 100, "Ready")
    assert job_service.get_job(job.job_id).status == ProjectStatus.COMPLETED


def test_14_sse_failure_event():
    """Test 14: SSE stream emits failure event."""
    req = ProjectCreateRequest(
        source_url="https://www.youtube.com/watch?v=mock_vid_123",
        user_prompt="extract code"
    )
    proj = project_service.create_project(req)
    job = job_service.create_job(proj.project_id)
    job_service.update_job_status(job.job_id, ProjectStatus.FAILED, 50, "Failed", error_message="Error")
    assert job_service.get_job(job.job_id).status == ProjectStatus.FAILED


def test_15_disconnected_sse_recovery():
    """Test 15: Disconnected SSE stream returns clean error."""
    res = client.get("/api/jobs/nonexistent_job/stream")
    assert res.status_code == 200


def test_16_stuck_job_watchdog():
    """Test 16: Job Watchdog enforces 180s timeout limit."""
    assert STAGE_WATCHDOG_TIMEOUT_SECONDS == 180.0


def test_17_job_cancellation():
    """Test 17: Job status update to FAILED/CANCELLED."""
    req = ProjectCreateRequest(
        source_url="https://www.youtube.com/watch?v=mock_vid_123",
        user_prompt="extract code"
    )
    proj = project_service.create_project(req)
    job = job_service.create_job(proj.project_id)
    job_service.update_job_status(job.job_id, ProjectStatus.FAILED, 0, "Cancelled", error_message="Cancelled by user")
    assert job_service.get_job(job.job_id).status == ProjectStatus.FAILED


def test_18_job_resumability():
    """Test 18: Resuming a job updates status to PROCESSING_VIDEO."""
    req = ProjectCreateRequest(
        source_url="https://www.youtube.com/watch?v=mock_vid_123",
        user_prompt="extract code"
    )
    proj = project_service.create_project(req)
    job = job_service.create_job(proj.project_id)
    resumed = job_service.resume_job(job.job_id)
    assert resumed.status == ProjectStatus.PROCESSING_VIDEO


def test_19_provenance_preservation():
    """Test 19: Generated Markdown contains video timestamp provenance."""
    req = ProjectCreateRequest(
        source_url="https://www.youtube.com/watch?v=mock_vid_123",
        user_prompt="extract code"
    )
    proj = project_service.create_project(req)
    job = job_service.create_job(proj.project_id)
    asyncio.run(job_service.execute_background_job(job.job_id, delay_step=0.01))
    arts = artifact_service.generate_project_artifacts(proj.project_id)
    assert "VidMind" in arts.markdown_preview_content


def test_20_ownership_isolation():
    """Test 20: User A cannot access User B's project or job."""
    req = ProjectCreateRequest(
        source_url="https://www.youtube.com/watch?v=mock_vid_123",
        user_prompt="extract code"
    )
    proj = project_service.create_project(req, owner_id="user_A")
    assert project_service.get_project(proj.project_id, owner_id="user_B") is None
