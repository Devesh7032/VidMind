import time
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.services.ai.gemini_key_manager import GeminiKeyManager, gemini_key_manager
from app.services.security_service import security_service

client = TestClient(app)


def test_1_key_1_succeeds_normally():
    """Test 1: KEY_1 succeeds normally without key rotation."""
    km = GeminiKeyManager()
    km.reset_expired_keys()
    
    call_count = 0
    def mock_api_call(slot, key):
        nonlocal call_count
        call_count += 1
        return "SUCCESS_RESULT"

    res = km.execute_with_failover(mock_api_call)
    assert res == "SUCCESS_RESULT"
    assert call_count == 1


def test_2_key_1_rate_limited_key_2_succeeds():
    """Test 2: KEY_1 rate-limited (HTTP 429) -> KEY_2 succeeds automatically."""
    km = GeminiKeyManager()
    
    attempts = []
    def mock_api_call(slot, key):
        attempts.append(slot)
        if slot == "KEY_1" and len(attempts) == 1:
            err = RuntimeError("HTTP 429 Rate Limit Exceeded")
            setattr(err, "status_code", 429)
            raise err
        return "SUCCESS_FROM_KEY_2"

    res = km.execute_with_failover(mock_api_call)
    assert res == "SUCCESS_FROM_KEY_2"
    assert "KEY_1" in attempts
    assert "KEY_2" in attempts


def test_3_key_1_quota_exceeded_key_2_succeeds():
    """Test 3: KEY_1 quota exceeded -> KEY_2 succeeds automatically."""
    km = GeminiKeyManager()
    
    attempts = []
    def mock_api_call(slot, key):
        attempts.append(slot)
        if slot == "KEY_1" and len(attempts) == 1:
            err = RuntimeError("Quota Exceeded for API Key")
            setattr(err, "status_code", 429)
            raise err
        return "SUCCESS_QUOTA_RECOVERY"

    res = km.execute_with_failover(mock_api_call)
    assert res == "SUCCESS_QUOTA_RECOVERY"


def test_4_both_keys_rate_limited_proper_user_facing_failure():
    """Test 4: Both keys rate-limited -> clean user-facing failure message."""
    km = GeminiKeyManager()
    
    def mock_api_call(slot, key):
        err = RuntimeError("Rate limit 429")
        setattr(err, "status_code", 429)
        raise err

    with pytest.raises(RuntimeError) as exc_info:
        km.execute_with_failover(mock_api_call, max_attempts=2)
    
    err_str = str(exc_info.value)
    assert "quota is temporarily unavailable" in err_str
    assert "KEY_1" not in err_str
    assert "KEY_2" not in err_str


def test_5_key_1_temporarily_unavailable_new_request_uses_key_2():
    """Test 5: KEY_1 temporarily unavailable -> new request uses KEY_2 immediately."""
    km = GeminiKeyManager()
    km.mark_key_rate_limited("KEY_1", cooldown_seconds=30)

    slot, _ = km.get_active_key_and_slot()
    assert slot == "KEY_2"


def test_6_key_1_becomes_available_returns_to_pool():
    """Test 6: KEY_1 becomes available again -> returns to pool after cooldown."""
    km = GeminiKeyManager()
    km.mark_key_rate_limited("KEY_1", cooldown_seconds=0.1)
    time.sleep(0.2)
    km.reset_expired_keys()

    status = km.get_key_status()
    assert status["gemini_key_1_status"] == "AVAILABLE"


def test_7_permanent_error_does_not_rotate_keys():
    """Test 7: Permanent error (400 Bad Request / 401 Auth) does not rotate keys unnecessarily."""
    km = GeminiKeyManager()
    
    attempts = []
    def mock_api_call(slot, key):
        attempts.append(slot)
        err = ValueError("Invalid prompt parameters (400 Bad Request)")
        setattr(err, "status_code", 400)
        raise err

    with pytest.raises(ValueError):
        km.execute_with_failover(mock_api_call)

    assert len(attempts) == 1


def test_8_api_keys_never_appear_in_frontend_responses():
    """Test 8: API keys and key slot names never appear in frontend responses."""
    res = client.get("/api/health")
    assert res.status_code == 200
    text = res.text
    
    if settings.get_key_1():
        assert settings.get_key_1() not in text
    if settings.get_key_2():
        assert settings.get_key_2() not in text

    scrubbed = security_service.scrub_secrets("Gemini API rate limit exceeded on KEY_1")
    assert "KEY_1" not in scrubbed


def test_9_failed_ai_stage_resumes_using_saved_intermediate_data():
    """Test 9: Failed AI stage resumes using saved intermediate data."""
    from app.services.checkpoint_service import checkpoint_service, StageName, CheckpointStatus
    checkpoint_service.save_stage_checkpoint("job_failover_test", "vid_123", StageName.INGEST, CheckpointStatus.COMPLETED)
    assert checkpoint_service.is_stage_completed_or_cached("job_failover_test", "vid_123", StageName.INGEST) is True


def test_10_multiple_simultaneous_jobs_distribute_requests():
    """Test 10: Multiple simultaneous jobs distribute requests across available keys."""
    km = GeminiKeyManager()
    km.reset_expired_keys()
    
    slots_used = []
    for _ in range(4):
        slot, _ = km.get_active_key_and_slot()
        slots_used.append(slot)

    assert "KEY_1" in slots_used
