import pytest
from app.services.ai.intent_engine import intent_engine
from app.services.ai.mock_provider import MockLLMProvider


@pytest.fixture(autouse=True)
def use_mock_ai_provider_for_tests():
    """
    Autouse fixture ensuring automated unit tests default to MockLLMProvider
    so test execution is deterministic, fast, and does not require an active LLM API key.
    """
    old_provider = intent_engine.get_provider()
    intent_engine.set_provider(MockLLMProvider())
    yield
    intent_engine.set_provider(old_provider)
