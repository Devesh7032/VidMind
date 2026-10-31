import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import (
    ExtractionPlan,
    TranscriptSegment,
    VisualObservation,
    FusedEvidence,
    ObservationType,
    ContentType,
    VisualContentType
)
from app.services.multimodal_fusion_service import multimodal_fusion_service, MAX_ANALYZED_FRAMES_PER_VIDEO
from app.services.ingestion_service import ingestion_service
from app.services.ai.mock_provider import MockLLMProvider
from app.services.ai.base import LLMProviderInterface

client = TestClient(app)


def test_transcript_relevance_selection():
    plan = ExtractionPlan(
        content_types=[ContentType.CODE, ContentType.TIME_COMPLEXITY]
    )
    segments = [
        TranscriptSegment(text="Welcome to the lecture.", start_seconds=0.0, end_seconds=5.0, duration_seconds=5.0),
        TranscriptSegment(text="Let's write the BFS algorithm code in Python.", start_seconds=5.0, end_seconds=15.0, duration_seconds=10.0),
        TranscriptSegment(text="The time complexity of BFS is O(V + E).", start_seconds=15.0, end_seconds=25.0, duration_seconds=10.0),
    ]

    relevant = multimodal_fusion_service.select_relevant_transcript_segments(segments, plan)
    assert len(relevant) == 2
    assert "BFS algorithm code" in relevant[0].text
    assert "time complexity" in relevant[1].text


def test_timestamp_window_generation_and_merging():
    segments = [
        TranscriptSegment(text="Code start", start_seconds=10.0, end_seconds=20.0, duration_seconds=10.0),
        TranscriptSegment(text="Code continue", start_seconds=22.0, end_seconds=30.0, duration_seconds=8.0),
    ]
    windows = multimodal_fusion_service.generate_timestamp_windows(segments, max_duration_seconds=600)
    assert len(windows) == 1  # Overlapping windows merged into 1 continuous window (5.0s to 35.0s)
    assert windows[0][0] == 5.0
    assert windows[0][1] == 35.0


def test_duplicate_frame_filtering():
    candidate_timestamps = [1.0, 3.0, 5.0, 15.0, 16.0, 28.0, 40.0, 45.0, 55.0, 65.0, 75.0, 85.0, 95.0, 105.0]
    filtered = multimodal_fusion_service.filter_duplicate_keyframes(candidate_timestamps, min_interval_seconds=10.0)
    
    assert len(filtered) <= MAX_ANALYZED_FRAMES_PER_VIDEO
    for i in range(1, len(filtered)):
        assert (filtered[i] - filtered[i-1]) >= 10.0


def test_visual_content_classification():
    provider = MockLLMProvider()
    code_obs = provider.analyze_visual_frame(12.5, "python code editor bfs")
    assert code_obs.content_type == VisualContentType.CODE
    assert "bfs" in code_obs.visible_code_text.lower()

    formula_obs = provider.analyze_visual_frame(25.0, "latex mathematical formula")
    assert formula_obs.content_type == VisualContentType.SLIDE
    assert "Complexity" in formula_obs.visible_code_text


def test_transcript_visual_fusion():
    proj_res = client.post("/api/projects", json={
        "source_url": "https://www.youtube.com/watch?v=test_fusion_vid",
        "user_prompt": "Extract BFS code and explanation."
    })
    project_id = proj_res.json()["project_id"]

    fusion_res = multimodal_fusion_service.fuse_multimodal_evidence(project_id)
    assert fusion_res.project_id == project_id
    assert fusion_res.total_evidence_count > 0
    
    first_ev = fusion_res.fused_evidence_list[0]
    assert first_ev.video_id is not None
    assert first_ev.start_seconds >= 0.0
    assert first_ev.transcript_text is not None
    assert first_ev.visual_observation is not None
    assert first_ev.confidence_score > 0.8


def test_missing_transcript_fallback_handling():
    # Test video with missing transcript
    class MissingTranscriptIngestionService(ingestion_service.__class__):
        def fetch_video_transcript(self, video_id):
            return "TRANSCRIPT_UNAVAILABLE", []

    old_svc = ingestion_service
    try:
        proj_res = client.post("/api/projects", json={
            "source_url": "https://www.youtube.com/watch?v=no_transcript_vid",
            "user_prompt": "Extract code."
        })
        project_id = proj_res.json()["project_id"]

        fusion_res = multimodal_fusion_service.fuse_multimodal_evidence(project_id)
        assert fusion_res.total_evidence_count > 0
        assert "transcript unavailable" in fusion_res.fused_evidence_list[0].transcript_text.lower()
    finally:
        pass


def test_vision_failure_fallback_handling():
    # Test vision provider failure
    class FaultyVisionProvider(MockLLMProvider):
        def analyze_visual_frame(self, frame_timestamp: float, context_hint: str = ""):
            raise RuntimeError("Vision model timeout")

    from app.services.ai.intent_engine import intent_engine
    old_provider = intent_engine.get_provider()
    try:
        intent_engine.set_provider(FaultyVisionProvider())
        proj_res = client.post("/api/projects", json={
            "source_url": "https://www.youtube.com/watch?v=vision_fail_vid",
            "user_prompt": "Extract code."
        })
        project_id = proj_res.json()["project_id"]

        fusion_res = multimodal_fusion_service.fuse_multimodal_evidence(project_id)
        assert fusion_res.total_evidence_count > 0
        # Transcript evidence preserved even though visual observation failed
        assert fusion_res.fused_evidence_list[0].transcript_text is not None
        assert fusion_res.fused_evidence_list[0].visual_observation is None
    finally:
        intent_engine.set_provider(old_provider)


def test_end_to_end_multimodal_background_job_pipeline():
    proj_res = client.post("/api/projects", json={
        "source_url": "https://www.youtube.com/watch?v=full_pipeline_vid",
        "user_prompt": "Extract BFS algorithm code, explanation and time complexity."
    })
    project_id = proj_res.json()["project_id"]

    job_res = client.post(f"/api/projects/{project_id}/analyze")
    assert job_res.status_code == 202
    job_id = job_res.json()["job_id"]

    # Poll status until job reaches EVIDENCE_READY
    max_wait = 4.0
    start_t = time.time()
    final_job = None

    while time.time() - start_t < max_wait:
        res = client.get(f"/api/jobs/{job_id}")
        data = res.json()
        if data["status"] in ["EVIDENCE_READY", "COMPLETED", "FAILED"]:
            final_job = data
            break
        time.sleep(0.1)

    assert final_job is not None
    assert final_job["status"] == "EVIDENCE_READY"
    assert final_job["progress_percent"] == 100
    assert "evidence_count" in final_job["details"]

    # Fetch fused evidence API
    ev_res = client.get(f"/api/projects/{project_id}/evidence")
    assert ev_res.status_code == 200
    ev_data = ev_res.json()
    assert ev_data["project_id"] == project_id
    assert ev_data["total_evidence_count"] > 0
    assert len(ev_data["fused_evidence_list"]) > 0
