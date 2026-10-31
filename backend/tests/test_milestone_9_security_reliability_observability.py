import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.security_service import security_service, SecurityError
from app.services.metrics_service import metrics_service
from app.services.project_service import project_service
from app.services.library_service import library_service
from app.schemas import ProjectCreateRequest, CollectionCreateRequest

client = TestClient(app)


def test_ssrf_youtube_url_validation():
    """Requirement 15, 16, 83: SSRF Protection blocks localhost, private IPs, metadata, and invalid protocols."""
    # SSRF Attack Attempts -> Must Raise SecurityError
    invalid_urls = [
        "http://localhost:8000/secret",
        "http://127.0.0.1/admin",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/internal",
        "file:///etc/passwd",
        "ftp://youtube.com/video",
        "javascript:alert(1)",
        "https://evil-domain.com/watch?v=12345"
    ]

    for bad_url in invalid_urls:
        with pytest.raises(SecurityError):
            security_service.validate_youtube_url(bad_url)

    # Valid Public YouTube URLs -> Must Pass
    valid_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/playlist?list=PLgUwDviBIf0oF6QL8m22w1hIDC1vJ_BHz"
    ]

    for good_url in valid_urls:
        res = security_service.validate_youtube_url(good_url)
        assert res == good_url


def test_input_size_limits():
    """Requirement 11, 12, 13, 14: Enforces strict length limits on prompts, chat messages, and pagination."""
    # Huge Prompt > 10,000 chars -> Rejected
    huge_prompt = "A" * 10001
    with pytest.raises(SecurityError):
        security_service.validate_prompt(huge_prompt)

    # Huge Chat Message > 4,000 chars -> Rejected
    huge_chat = "B" * 4001
    with pytest.raises(SecurityError):
        security_service.validate_chat_message(huge_chat)

    # Search Pagination Page Size -> Capped at MAX_PAGE_SIZE (50)
    page, size = security_service.validate_pagination(page=1, page_size=99999)
    assert page == 1
    assert size == 50


def test_ownership_isolation_and_idor_protection():
    """Requirement 8, 9, 83: User A's resources cannot be accessed by User B."""
    headers_user_a = {"X-User-ID": "user_alice"}
    headers_user_b = {"X-User-ID": "user_bob"}

    # User Alice creates a project
    proj_a = project_service.create_project(
        ProjectCreateRequest(
            source_url="https://www.youtube.com/watch?v=alice_vid_123",
            user_prompt="Alice prompt"
        ),
        owner_id="user_alice"
    )

    # User Alice can fetch her project
    res_a = client.get(f"/api/projects/{proj_a.project_id}", headers=headers_user_a)
    assert res_a.status_code == 200

    # User Bob attempting to fetch Alice's project -> Access Denied / 404
    res_b = client.get(f"/api/projects/{proj_a.project_id}", headers=headers_user_b)
    assert res_b.status_code == 404

    # User Alice creates a collection
    coll_a = library_service.create_collection(
        CollectionCreateRequest(name="Alice DSA Notes", owner_id="user_alice")
    )

    # User Bob cannot access Alice's collection
    res_coll_b = client.get(f"/api/collections/{coll_a.collection_id}", headers=headers_user_b)
    assert res_coll_b.status_code == 404


def test_secret_scrubbing():
    """Requirement 20, 21, 83: Excludes API keys and secret tokens from outputs and exceptions."""
    secret_text = "Error calling Gemini with key AIzaSyA123456789_SecretKey_Value"
    scrubbed = security_service.scrub_secrets(secret_text)
    assert "AIzaSyA123456789_SecretKey_Value" not in scrubbed or "[REDACTED_SECRET]" in scrubbed


def test_health_ready_diagnostics_endpoints():
    """Requirement 41, 42, 80: Liveness, Readiness, and Operational Diagnostics endpoints."""
    # Liveness check
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"

    # Readiness check
    res_ready = client.get("/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "ready"

    # Diagnostics endpoint
    res_diag = client.get("/api/diagnostics")
    assert res_diag.status_code == 200
    diag_data = res_diag.json()
    assert "metrics" in diag_data
    assert "cache" in diag_data


def test_request_correlation_id_middleware():
    """Requirement 45, 46, 85: Generates or propagates X-Request-ID header on all responses."""
    custom_req_id = "req_test_correlation_999"
    res = client.get("/health", headers={"X-Request-ID": custom_req_id})
    assert res.status_code == 200
    assert res.headers.get("X-Request-ID") == custom_req_id

    # Auto-generated request ID
    res_auto = client.get("/health")
    assert "X-Request-ID" in res_auto.headers
    assert res_auto.headers["X-Request-ID"].startswith("req_")


def test_metrics_collection():
    """Requirement 49, 50, 85: Tracks HTTP requests, latencies, cache hits/misses, and job metrics."""
    metrics = metrics_service.get_metrics_summary()
    assert "http" in metrics
    assert "cache" in metrics
    assert "jobs" in metrics
    assert "gemini" in metrics
    assert metrics["http"]["total_requests"] >= 1
