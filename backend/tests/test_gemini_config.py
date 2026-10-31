import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.services.ai.gemini_provider import GeminiLLMProvider
from app.services.ai.mock_provider import MockLLMProvider
from app.services.ai.intent_engine import IntentEngine, intent_engine
from app.schemas import ExtractionPlan, IntentCategory

client = TestClient(app)


def test_gemini_api_key_loading_from_settings():
    """Verify settings loads GEMINI_API_KEY_1 and GEMINI_API_KEY_2 from environment/.env."""
    assert hasattr(settings, "gemini_api_key_1")
    assert hasattr(settings, "gemini_api_key_2")
    assert isinstance(settings.get_key_1(), str)


def test_missing_gemini_key_behavior():
    """Verify GeminiLLMProvider raises clear ValueError when GEMINI_API_KEY_1 is unconfigured."""
    provider = GeminiLLMProvider()
    with patch.object(settings, "gemini_api_key_1", ""), patch.object(settings, "gemini_api_key", ""):
        with pytest.raises(ValueError) as exc_info:
            provider.generate_intent_plan("Extract BFS code.")
        assert "Gemini API key is not configured" in str(exc_info.value)


def test_gemini_provider_initialization_and_naming():
    """Verify GeminiLLMProvider initializes and returns correct provider name."""
    provider = GeminiLLMProvider()
    assert provider.get_provider_name() == "gemini_provider"


def test_intent_engine_provider_selection():
    """Verify IntentEngine respects custom provider setting (e.g. MockLLMProvider for tests)."""
    engine = IntentEngine(provider=MockLLMProvider())
    assert engine.get_provider().get_provider_name() == "mock_provider"

    engine.set_provider(GeminiLLMProvider())
    assert engine.get_provider().get_provider_name() == "gemini_provider"


def test_health_check_safe_gemini_status_non_exposure():
    """Verify /api/health reports CONFIGURED/NOT CONFIGURED without exposing API keys or secrets."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "gemini_key_1_status" in data
    assert "gemini_key_2_status" in data
    assert data["gemini_key_1_status"] in ["CONFIGURED", "NOT CONFIGURED"]

    # Security Assertion: API key value or length must never be in health response text
    raw_response_text = response.text
    if settings.get_key_1():
        assert settings.get_key_1() not in raw_response_text


def test_gemini_api_auth_failure_handling():
    """Verify 401/403 HTTP error raises user-friendly auth error without leaking secrets."""
    provider = GeminiLLMProvider()
    
    mock_response = MagicMock()
    mock_response.status_code = 401
    
    with patch("httpx.Client.post", return_value=mock_response):
        with pytest.raises(ValueError) as exc_info:
            provider.generate_intent_plan("Extract code.")
        err_msg = str(exc_info.value)
        assert "authentication failed" in err_msg.lower()
        if settings.get_key_1():
            assert settings.get_key_1() not in err_msg


def test_gemini_api_rate_limit_handling():
    """Verify 429 rate limit HTTP error triggers key manager failover or raises user-friendly rate limit error."""
    provider = GeminiLLMProvider()
    
    mock_response = MagicMock()
    mock_response.status_code = 429
    
    with patch("httpx.Client.post", return_value=mock_response):
        with pytest.raises(RuntimeError) as exc_info:
            provider.generate_intent_plan("Extract code.")
        assert "rate limit" in str(exc_info.value).lower()


def test_gemini_api_timeout_handling():
    """Verify request timeout raises user-friendly error."""
    provider = GeminiLLMProvider()
    
    import httpx
    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Connection timed out")):
        with pytest.raises(RuntimeError) as exc_info:
            provider.generate_intent_plan("Extract code.")
        assert "timed out" in str(exc_info.value).lower() or "failed across" in str(exc_info.value).lower()


def test_verify_connectivity_safe_output():
    """Verify verify_connectivity returns safe dict without revealing secret key."""
    provider = GeminiLLMProvider()
    conn_result = provider.verify_connectivity()
    assert "status" in conn_result
    assert "message" in conn_result
    if settings.get_key_1():
        assert settings.get_key_1() not in str(conn_result)
