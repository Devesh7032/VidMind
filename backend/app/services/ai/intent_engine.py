from typing import Optional, Any
from app.services.ai.base import LLMProviderInterface
from app.services.ai.provider_manager import provider_manager, AIProviderManager
from app.schemas import ExtractionPlan


class IntentEngine:
    """
    VidMind Intent Engine.
    Converts natural-language user prompts into a schema-validated ExtractionPlan
    using the AIProviderManager orchestration layer (Dual Gemini Keys).
    """

    def __init__(self, provider: Optional[Any] = None):
        self._provider = provider or provider_manager

    def get_provider(self):
        return self._provider

    def set_provider(self, provider):
        self._provider = provider

    def create_extraction_plan(self, prompt: str) -> ExtractionPlan:
        prompt = prompt.strip()
        if not prompt or len(prompt) < 3:
            raise ValueError("User prompt must be at least 3 characters long.")

        plan = self._provider.generate_intent_plan(prompt)
        if not isinstance(plan, ExtractionPlan):
            plan = ExtractionPlan(**dict(plan))
        return plan


# Global singleton instance for Intent Engine
intent_engine = IntentEngine()
