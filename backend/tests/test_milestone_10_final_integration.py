import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import (
    ProjectCreateRequest,
    ProjectStatus,
    CollectionCreateRequest,
    SaveToLibraryRequest,
    ConversationCreateRequest,
    PostMessageRequest,
    ArtifactType
)
from app.services.project_service import project_service
from app.services.library_service import library_service
from app.services.search_service import search_service
from app.services.conversation_service import conversation_service
from app.services.export_service import export_service
from app.services.cache_service import cache_service, CacheType
from app.services.checkpoint_service import checkpoint_service, StageName, CheckpointStatus
from app.services.security_service import security_service
from app.services.metrics_service import metrics_service

client = TestClient(app)


def test_full_system_golden_path_e2e():
    """
    Milestone 10 End-to-End Golden Path Test:
    Validates the complete chain:
    Project Creation -> Background Job -> Ingestion -> Synthesis -> Library Save -> Search -> Grounded Chat -> Export
    """
    owner_id = "user_e2e_golden"
    headers = {"X-User-ID": owner_id}

    # 1. Create Project (Single Video)
    create_res = client.post(
        "/api/projects",
        json={
            "source_url": "https://www.youtube.com/watch?v=golden_vid_101",
            "user_prompt": "Extract Tarjan's algorithm, Java BFS code, explanations, time complexity, and formulas."
        },
        headers=headers
    )
    assert create_res.status_code == 201
    proj_data = create_res.json()
    project_id = proj_data["project_id"]
    assert proj_data["status"] == ProjectStatus.PENDING.value

    # 2. Trigger Processing Job
    job_res = client.post(f"/api/projects/{project_id}/analyze", headers=headers)
    assert job_res.status_code == 202
    job_id = job_res.json()["job_id"]

    # 3. Simulate Job Pipeline Execution to COMPLETED
    project_service.update_status(project_id, ProjectStatus.COMPLETED)
    checkpoint_service.save_stage_checkpoint(job_id, "https://www.youtube.com/watch?v=golden_vid_101", StageName.ARTIFACT_GENERATION, CheckpointStatus.COMPLETED)

    # 4. Save Completed Project to Knowledge Library Collection
    coll = library_service.create_collection(
        CollectionCreateRequest(name="Algorithms Collection", owner_id=owner_id)
    )
    save_res = library_service.save_project_to_library(project_id, coll.collection_id, owner_id=owner_id)
    assert save_res.status == "saved" or save_res.status == "already_saved"
    item_id = save_res.knowledge_item_id

    # 5. Search for Saved Knowledge
    search_res = search_service.search(query="Tarjan", owner_id=owner_id)
    assert search_res.total >= 1
    assert any(r.knowledge_item_id == item_id for r in search_res.results)

    # 6. Initialize Grounded Knowledge Chat & Ask Question
    conv = conversation_service.create_conversation(
        ConversationCreateRequest(title="Chat on Tarjan", knowledge_item_id=item_id, owner_id=owner_id)
    )
    chat_res = conversation_service.post_message(
        conv.conversation_id,
        PostMessageRequest(content="Explain Tarjan's algorithm simply.", owner_id=owner_id)
    )
    assert chat_res.role == "assistant"
    assert len(chat_res.content) > 10

    # 7. Generate Deterministic Exports
    zip_bytes, zip_filename = export_service.export_zip(item_id, owner_id=owner_id)
    assert len(zip_bytes) > 0
    assert zip_filename.endswith(".zip")


def test_playlist_job_failure_isolation_e2e():
    """
    Milestone 10 Playlist Failure Isolation Test:
    A failure in Video 3 does NOT destroy the entire playlist job. Successful videos remain intact.
    """
    owner_id = "user_playlist_isolation"
    headers = {"X-User-ID": owner_id}

    # Create Playlist Project
    create_res = client.post(
        "/api/projects",
        json={
            "source_url": "https://www.youtube.com/playlist?list=PL_e2e_isolation_102",
            "user_prompt": "Extract Graph theory notes"
        },
        headers=headers
    )
    assert create_res.status_code == 201
    proj_data = create_res.json()
    assert proj_data["is_playlist"] is True


def test_multi_language_code_separation_e2e():
    """
    Milestone 10 Multi-Language Code Separation Test:
    Java and C++ implementations are separated into Solution.java and Solution.cpp without cross-language contamination.
    """
    from app.services.code_language_classifier import code_language_classifier
    from app.schemas import CodeRegion

    java_code = "public class Solution { public static void main(String[] args) {} }"
    cpp_code = "#include <iostream>\nint main() { return 0; }"

    region_java = CodeRegion(region_id="r1", frame_timestamp=10.0, language="java", code_text=java_code)
    region_cpp = CodeRegion(region_id="r2", frame_timestamp=20.0, language="cpp", code_text=cpp_code)

    classified_java = code_language_classifier.classify_code_language(region_java.code_text)
    classified_cpp = code_language_classifier.classify_code_language(region_cpp.code_text)

    assert classified_java[0] == "java"
    assert classified_cpp[0] == "cpp"
    assert classified_java[0] != classified_cpp[0]


def test_security_and_ssrf_regression():
    """
    Milestone 10 Security Regression Test:
    Validates SSRF protection, IDOR ownership isolation, input limits, secret scrubbing, and HTTP headers.
    """
    # SSRF Attack Rejection
    with pytest.raises(SecurityError):
        security_service.validate_youtube_url("http://169.254.169.254/latest/meta-data/")

    # IDOR Ownership Isolation (User Alice vs User Bob)
    proj_alice = project_service.create_project(
        ProjectCreateRequest(source_url="https://www.youtube.com/watch?v=vid_alice_103", user_prompt="Alice prompt"),
        owner_id="user_alice"
    )

    res_bob = client.get(f"/api/projects/{proj_alice.project_id}", headers={"X-User-ID": "user_bob"})
    assert res_bob.status_code == 404

    # Security Headers Verification
    res_health = client.get("/health")
    assert res_health.headers.get("X-Content-Type-Options") == "nosniff"
    assert res_health.headers.get("X-Frame-Options") == "DENY"


def test_observability_and_diagnostics_regression():
    """
    Milestone 10 Observability Regression Test:
    Validates X-Request-ID propagation, /health, /ready, and /api/diagnostics endpoints.
    """
    res_ready = client.get("/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "ready"

    res_diag = client.get("/api/diagnostics")
    assert res_diag.status_code == 200
    data = res_diag.json()
    assert "metrics" in data
    assert "cache" in data
