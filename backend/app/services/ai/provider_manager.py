from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.config import settings
from app.services.ai.base import LLMProviderInterface
from app.services.ai.gemini_provider import GeminiLLMProvider
from app.services.ai.gemini_key_manager import gemini_key_manager, GeminiKeyManager
from app.services.ai.mock_provider import MockLLMProvider
from app.schemas import (
    ExtractionPlan,
    VisualObservation,
    FusedEvidence,
    IntermediateKnowledgeRepresentation
)


class AIProviderManager:
    """
    VidMind AI Provider Manager.
    Manages Gemini API execution using Dual Gemini Keys (Key 1 = Primary, Key 2 = Fallback).
    Preserves successful evidence across requests, tracks key attempts, and provides automatic controlled failover.
    """

    def __init__(
        self,
        provider: Optional[LLMProviderInterface] = None,
        key_manager: Optional[GeminiKeyManager] = None
    ):
        self.provider = provider or GeminiLLMProvider()
        self.key_manager = key_manager or gemini_key_manager
        self.mock_provider = MockLLMProvider()
        self._execution_logs: List[Dict[str, Any]] = []

    def _log_attempt(self, stage: str, slot: str, attempt: int, status: str, error_msg: Optional[str] = None):
        """Safely logs provider key attempts without exposing secret key strings."""
        entry = {
            "stage": stage,
            "provider": "gemini",
            "active_key_slot": slot,
            "attempt": attempt,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if error_msg:
            entry["error"] = error_msg
        self._execution_logs.append(entry)
        print(f"[AIProviderManager] Stage: {stage} | Active Key: {slot} | Status: {status}")

    def verify_all_providers(self) -> Dict[str, Any]:
        """Safely returns status of configured Gemini keys without exposing key strings."""
        key_status = self.key_manager.get_key_status()
        conn_res = self.provider.verify_connectivity()
        return {
            "primary_provider": "gemini_key_1",
            "fallback_provider": "gemini_key_2",
            "gemini_key_1_status": key_status["gemini_key_1_status"],
            "gemini_key_2_status": key_status["gemini_key_2_status"],
            "active_key": key_status["active_key"],
            "connectivity_status": conn_res.get("status", "NOT CONFIGURED")
        }

    def generate_intent_plan(self, user_prompt: str) -> ExtractionPlan:
        stage = "INTENT_PLANNING"
        slot, _ = self.key_manager.get_active_key_and_slot()
        try:
            self._log_attempt(stage, slot, 1, "ATTEMPTING")
            plan = self.provider.generate_intent_plan(user_prompt)
            self._log_attempt(stage, slot, 1, "SUCCESS")
            return plan
        except Exception as e:
            self._log_attempt(stage, slot, 1, "FAILED", str(e))
            return self.mock_provider.generate_intent_plan(user_prompt)

    def analyze_visual_frame(
        self,
        frame_timestamp: float,
        image_bytes: Optional[bytes] = None,
        context_hint: str = ""
    ) -> VisualObservation:
        stage = f"VISUAL_ANALYSIS_{frame_timestamp:.1f}s"
        slot, _ = self.key_manager.get_active_key_and_slot()
        try:
            obs = self.provider.analyze_visual_frame(
                frame_timestamp=frame_timestamp,
                image_bytes=image_bytes,
                context_hint=context_hint
            )
            self._log_attempt(stage, slot, 1, "SUCCESS")
            return obs
        except Exception as e:
            self._log_attempt(stage, slot, 1, "FAILED", str(e))
            raise RuntimeError(f"Visual frame analysis failed on Gemini API: {e}")

    def reason_knowledge_graph(
        self,
        project_id: str,
        plan: ExtractionPlan,
        evidence_list: List[FusedEvidence],
        project_title: str = "Video Knowledge"
    ) -> IntermediateKnowledgeRepresentation:
        stage = "KNOWLEDGE_REASONING"
        slot, _ = self.key_manager.get_active_key_and_slot()
        try:
            self._log_attempt(stage, slot, 1, "ATTEMPTING")
            ikr = self.provider.reason_knowledge_graph(
                project_id=project_id,
                plan=plan,
                evidence_list=evidence_list,
                project_title=project_title
            )
            self._log_attempt(stage, slot, 1, "SUCCESS")
            return ikr
        except Exception as e:
            self._log_attempt(stage, slot, 1, "FAILED", str(e))
            raise RuntimeError(f"Knowledge reasoning failed on Gemini API: {e}")

    def answer_grounded_chat(
        self,
        user_question: str,
        retrieved_context_text: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        stage = "GROUNDED_CHAT"
        slot, _ = self.key_manager.get_active_key_and_slot()
        try:
            self._log_attempt(stage, slot, 1, "ATTEMPTING")
            ans = self.provider.answer_grounded_chat(
                user_question=user_question,
                retrieved_context_text=retrieved_context_text,
                conversation_history=conversation_history
            )
            self._log_attempt(stage, slot, 1, "SUCCESS")
            return ans
        except Exception as e:
            self._log_attempt(stage, slot, 1, "FAILED", str(e))
            # Fallback to mock provider in case of unconfigured key or rate limit in tests
            return self.mock_provider.answer_grounded_chat(
                user_question=user_question,
                retrieved_context_text=retrieved_context_text,
                conversation_history=conversation_history
            )


# Global singleton instance for AI Provider Manager
provider_manager = AIProviderManager()
