from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from app.schemas import (
    ExtractionPlan,
    VisualObservation,
    FusedEvidence,
    IntermediateKnowledgeRepresentation
)


class LLMProviderInterface(ABC):
    """
    Abstract AI Provider Interface decoupling VidMind core services
    from specific LLM vendors (Gemini, OpenAI, Anthropic, local models).
    """

    @abstractmethod
    def generate_intent_plan(self, user_prompt: str) -> ExtractionPlan:
        """
        Parses a natural-language user prompt into a schema-validated ExtractionPlan.
        """
        pass

    @abstractmethod
    def analyze_visual_frame(
        self,
        frame_timestamp: float,
        image_bytes: Optional[bytes] = None,
        context_hint: str = ""
    ) -> VisualObservation:
        """
        Analyzes a selected visual keyframe image and returns a structured VisualObservation.
        """
        pass

    @abstractmethod
    def reason_knowledge_graph(
        self,
        project_id: str,
        plan: ExtractionPlan,
        evidence_list: List[FusedEvidence],
        project_title: str = "Video Knowledge"
    ) -> IntermediateKnowledgeRepresentation:
        """
        Reasons over fused multimodal evidence to construct an IntermediateKnowledgeRepresentation (IKR).
        """
        pass

    @abstractmethod
    def answer_grounded_chat(
        self,
        user_question: str,
        retrieved_context_text: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generates a grounded answer for a user question based STRICTLY on retrieved saved knowledge context.
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns the name of the AI provider (e.g. 'gemini', 'openai', 'mock')."""
        pass
