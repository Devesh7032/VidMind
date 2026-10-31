import ast
import uuid
from typing import List, Optional, Dict, Any
from app.services.ai.base import LLMProviderInterface
from app.schemas import (
    ExtractionPlan,
    IntentCategory,
    ContentType,
    ArtifactType,
    OrganizationStrategy,
    VisualObservation,
    VisualContentType,
    FusedEvidence,
    ObservationType,
    CodeSnippet,
    ComplexityAnalysis,
    EvidenceReference,
    KnowledgeNode,
    IntermediateKnowledgeRepresentation,
    SyntaxValidity
)


class MockLLMProvider(LLMProviderInterface):
    """
    Deterministic Mock Provider used ONLY for automated unit tests,
    CI environments, and offline test execution.
    """

    def get_provider_name(self) -> str:
        return "mock_provider"

    def analyze_visual_frame(
        self,
        frame_timestamp: float,
        image_bytes: Optional[bytes] = None,
        context_hint: str = ""
    ) -> VisualObservation:
        hint_lower = context_hint.lower()

        if "code" in hint_lower or "bfs" in hint_lower or "python" in hint_lower or "algorithm" in hint_lower:
            return VisualObservation(
                frame_timestamp=frame_timestamp,
                content_type=VisualContentType.CODE,
                description=f"Code editor showing algorithm implementation near {frame_timestamp:.1f}s",
                visible_code_text="from collections import deque\ndef bfs(graph, start):\n    visited = set([start])\n    queue = deque([start])\n    while queue:\n        node = queue.popleft()\n        for neighbor in graph[node]:\n            if neighbor not in visited:\n                visited.add(neighbor)\n                queue.append(neighbor)\n    return visited",
                confidence_score=0.95
            )
        elif "formula" in hint_lower or "math" in hint_lower:
            return VisualObservation(
                frame_timestamp=frame_timestamp,
                content_type=VisualContentType.SLIDE,
                description=f"Slide presentation showing mathematical formulas near {frame_timestamp:.1f}s",
                visible_code_text="Time Complexity: O(V + E)\nSpace Complexity: O(V)",
                confidence_score=0.92
            )
        elif "terminal" in hint_lower or "command" in hint_lower:
            return VisualObservation(
                frame_timestamp=frame_timestamp,
                content_type=VisualContentType.TERMINAL,
                description=f"Terminal window executing shell commands near {frame_timestamp:.1f}s",
                visible_code_text="$ python main.py --run-bfs",
                confidence_score=0.89
            )
        else:
            return VisualObservation(
                frame_timestamp=frame_timestamp,
                content_type=VisualContentType.GENERAL,
                description=f"Educational visual demonstration keyframe near {frame_timestamp:.1f}s",
                visible_code_text=None,
                confidence_score=0.85
            )

    def generate_intent_plan(self, user_prompt: str) -> ExtractionPlan:
        prompt_lower = user_prompt.lower().strip()

        if "ignore previous instructions" in prompt_lower or "system:" in prompt_lower or "eval(" in prompt_lower:
            return ExtractionPlan(
                intent_category=IntentCategory.CUSTOM,
                content_types=[ContentType.CONCEPTS],
                target_artifact_types=[ArtifactType.MARKDOWN_DOCUMENT],
                organization_strategy=OrganizationStrategy.TOPIC_HIERARCHY,
                custom_instructions="Sanitized request processed safely.",
                human_readable_summary="I'll extract key educational concepts while filtering untrusted instructions."
            )

        if "code" in prompt_lower or "function" in prompt_lower or "script" in prompt_lower or "python" in prompt_lower:
            content_types = [ContentType.CODE, ContentType.CONCEPTS]
            if "complexity" in prompt_lower or "time" in prompt_lower:
                content_types.extend([ContentType.TIME_COMPLEXITY, ContentType.SPACE_COMPLEXITY])
            if "example" in prompt_lower:
                content_types.append(ContentType.EXAMPLES)
            
            return ExtractionPlan(
                intent_category=IntentCategory.CODE_EXTRACTION,
                content_types=list(dict.fromkeys(content_types)),
                target_artifact_types=[ArtifactType.MARKDOWN_DOCUMENT, ArtifactType.CODE_FILES],
                organization_strategy=OrganizationStrategy.TOPIC_HIERARCHY,
                custom_instructions="Extract runnable code implementations with explanations.",
                human_readable_summary="I'll extract the code implementations, explanations, and complexity analysis as structured notes and runnable files."
            )

        if "formula" in prompt_lower or "math" in prompt_lower or "equation" in prompt_lower:
            return ExtractionPlan(
                intent_category=IntentCategory.FORMULA_SHEET,
                content_types=[ContentType.FORMULAS, ContentType.DEFINITIONS, ContentType.EXAMPLES],
                target_artifact_types=[ArtifactType.MARKDOWN_DOCUMENT],
                organization_strategy=OrganizationStrategy.TOPIC_HIERARCHY,
                custom_instructions="Extract LaTeX mathematical formulas with variable definitions.",
                human_readable_summary="I'll extract all mathematical formulas, variable definitions, and step-by-step proofs."
            )

        if "interview" in prompt_lower or "question" in prompt_lower or "answer" in prompt_lower or "q&a" in prompt_lower:
            return ExtractionPlan(
                intent_category=IntentCategory.INTERVIEW_PREP,
                content_types=[ContentType.QUESTIONS_ANSWERS, ContentType.CONCEPTS, ContentType.CODE],
                target_artifact_types=[ArtifactType.MARKDOWN_DOCUMENT],
                organization_strategy=OrganizationStrategy.QUESTION_ANSWER_PAIRS,
                custom_instructions="Structure extracted content into Q&A format for technical interview preparation.",
                human_readable_summary="I'll extract key interview questions and detailed answers organized by topic."
            )

        if "flashcard" in prompt_lower or "anki" in prompt_lower or "deck" in prompt_lower:
            return ExtractionPlan(
                intent_category=IntentCategory.FLASHCARDS,
                content_types=[ContentType.DEFINITIONS, ContentType.CONCEPTS, ContentType.QUESTIONS_ANSWERS],
                target_artifact_types=[ArtifactType.ANKI_CSV, ArtifactType.MARKDOWN_DOCUMENT],
                organization_strategy=OrganizationStrategy.QUESTION_ANSWER_PAIRS,
                custom_instructions="Generate definition flashcards.",
                human_readable_summary="I'll convert key definitions and concepts into flashcard format for quick review."
            )

        if "revision" in prompt_lower or "exam" in prompt_lower or "lecture" in prompt_lower or "notes" in prompt_lower:
            return ExtractionPlan(
                intent_category=IntentCategory.EXAM_REVISION if "exam" in prompt_lower else IntentCategory.STUDY_NOTES,
                content_types=[ContentType.CONCEPTS, ContentType.EXAMPLES, ContentType.DEFINITIONS],
                target_artifact_types=[ArtifactType.MARKDOWN_DOCUMENT],
                organization_strategy=OrganizationStrategy.TOPIC_HIERARCHY,
                custom_instructions="Create comprehensive study notes.",
                human_readable_summary="I'll create detailed revision notes covering main concepts and key examples."
            )

        return ExtractionPlan(
            intent_category=IntentCategory.STUDY_NOTES,
            content_types=[ContentType.CONCEPTS, ContentType.EXAMPLES, ContentType.DEFINITIONS],
            target_artifact_types=[ArtifactType.MARKDOWN_DOCUMENT],
            organization_strategy=OrganizationStrategy.TOPIC_HIERARCHY,
            custom_instructions="Create structured general revision notes.",
            human_readable_summary="I'll summarize the main concepts, key demonstrations, and explanations from this video."
        )

    def _validate_python_syntax(self, code: str) -> SyntaxValidity:
        """Static non-executing AST syntax validation."""
        try:
            ast.parse(code)
            return SyntaxValidity.VERIFIED
        except SyntaxError:
            return SyntaxValidity.SYNTAX_ERROR
        except Exception:
            return SyntaxValidity.UNVERIFIED_FRAGMENT

    def reason_knowledge_graph(
        self,
        project_id: str,
        plan: ExtractionPlan,
        evidence_list: List[FusedEvidence],
        project_title: str = "Video Knowledge"
    ) -> IntermediateKnowledgeRepresentation:
        global_provenance: List[EvidenceReference] = []
        topic_nodes: List[KnowledgeNode] = []

        for ev in evidence_list:
            ref = EvidenceReference(
                evidence_id=ev.evidence_id,
                video_id=ev.video_id,
                start_seconds=ev.start_seconds,
                end_seconds=ev.end_seconds,
                observation_type=ev.observation_type,
                confidence_score=ev.confidence_score
            )
            global_provenance.append(ref)

        if plan.intent_category == IntentCategory.CODE_EXTRACTION or ContentType.CODE in plan.content_types:
            sample_code = (
                "from collections import deque\n\n"
                "def bfs(graph, start):\n"
                "    \"\"\"Breadth-First Search Algorithm\"\"\"\n"
                "    visited = set([start])\n"
                "    queue = deque([start])\n\n"
                "    while queue:\n"
                "        vertex = queue.popleft()\n"
                "        for neighbor in graph[vertex]:\n"
                "            if neighbor not in visited:\n"
                "                visited.add(neighbor)\n"
                "                queue.append(neighbor)\n"
                "    return visited\n"
            )
            syntax_val = self._validate_python_syntax(sample_code)

            code_snippet = CodeSnippet(
                filename="bfs.py",
                language="python",
                code_content=sample_code,
                start_seconds=evidence_list[0].start_seconds if evidence_list else 5.0,
                end_seconds=evidence_list[0].end_seconds if evidence_list else 25.0,
                reconstruction_status=ObservationType.DIRECTLY_OBSERVED,
                syntax_validity=syntax_val
            )

            complexity = ComplexityAnalysis(
                time_complexity="O(V + E)",
                space_complexity="O(V)",
                explanation="V is the number of vertices and E is the number of edges. Queue stores up to V vertices.",
                observation_type=ObservationType.DIRECTLY_OBSERVED
            )

            topic_nodes.append(KnowledgeNode(
                node_id=f"node_{uuid.uuid4().hex[:8]}",
                topic_title="Breadth-First Search (BFS)",
                concept_summary="BFS explores graph nodes level-by-level using a FIFO queue structure. Ideal for unweighted shortest paths.",
                key_examples=["Shortest path traversal in unweighted graphs", "Level-order tree traversal"],
                formulas=[],
                questions_and_answers=[],
                code_snippets=[code_snippet],
                complexities=complexity,
                evidence_references=global_provenance[:2] if global_provenance else [],
                observation_type=ObservationType.DIRECTLY_OBSERVED,
                confidence_score=0.96
            ))

        elif plan.intent_category == IntentCategory.FORMULA_SHEET or ContentType.FORMULAS in plan.content_types:
            topic_nodes.append(KnowledgeNode(
                node_id=f"node_{uuid.uuid4().hex[:8]}",
                topic_title="Mathematical Formulations & Analysis",
                concept_summary="Key equations and mathematical definitions presented in the lecture.",
                key_examples=["Graph edge count bound: E <= V(V-1)/2"],
                formulas=["T(V, E) = O(V + E)", "S(V) = O(V)"],
                questions_and_answers=[],
                code_snippets=[],
                complexities=ComplexityAnalysis(
                    time_complexity="O(V + E)",
                    space_complexity="O(V)",
                    explanation="Stated formula for algorithm complexity.",
                    observation_type=ObservationType.DIRECTLY_OBSERVED
                ),
                evidence_references=global_provenance[:2] if global_provenance else [],
                observation_type=ObservationType.DIRECTLY_OBSERVED,
                confidence_score=0.93
            ))

        elif plan.intent_category == IntentCategory.INTERVIEW_PREP or ContentType.QUESTIONS_ANSWERS in plan.content_types:
            qna = [
                {
                    "question": "What data structure is used to implement BFS?",
                    "answer": "BFS uses a Queue (FIFO) data structure to explore vertices level-by-level."
                },
                {
                    "question": "What is the time complexity of BFS on an adjacency list?",
                    "answer": "The time complexity is O(V + E) where V is vertices and E is edges."
                }
            ]
            topic_nodes.append(KnowledgeNode(
                node_id=f"node_{uuid.uuid4().hex[:8]}",
                topic_title="Graph Algorithm Technical Interview Q&A",
                concept_summary="Core interview questions and optimal answers extracted from lecture content.",
                key_examples=["BFS queue traversal", "Visited set loop detection"],
                formulas=[],
                questions_and_answers=qna,
                code_snippets=[],
                complexities=None,
                evidence_references=global_provenance[:2] if global_provenance else [],
                observation_type=ObservationType.DIRECTLY_OBSERVED,
                confidence_score=0.95
            ))

        else:
            topic_nodes.append(KnowledgeNode(
                node_id=f"node_{uuid.uuid4().hex[:8]}",
                topic_title="Core Lecture Concepts",
                concept_summary="Comprehensive explanation of graph algorithms, traversal mechanisms, and key data structures.",
                key_examples=["Graph traversal demo", "Adjacency matrix vs list representation"],
                formulas=[],
                questions_and_answers=[],
                code_snippets=[],
                complexities=ComplexityAnalysis(
                    time_complexity="O(V + E)",
                    space_complexity="O(V)",
                    explanation="Derived algorithm complexity.",
                    observation_type=ObservationType.AI_INFERRED
                ),
                evidence_references=global_provenance[:2] if global_provenance else [],
                observation_type=ObservationType.DIRECTLY_OBSERVED,
                confidence_score=0.91
            ))

        return IntermediateKnowledgeRepresentation(
            project_id=project_id,
            title=project_title,
            intent_category=plan.intent_category,
            topic_nodes=topic_nodes,
            global_provenance=global_provenance
        )

    def answer_grounded_chat(
        self,
        user_question: str,
        retrieved_context_text: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Deterministic mock response for automated testing."""
        q_low = user_question.lower()
        if not retrieved_context_text or "NO_RELEVANT_KNOWLEDGE_FOUND" in retrieved_context_text:
            return "I couldn't find that information in your saved knowledge."

        if "complexity" in q_low or "time" in q_low:
            return "Based on your saved knowledge, the time complexity is O(V + E)."
        elif "java" in q_low:
            return "Based on your saved knowledge, here is the Java implementation:\n```java\nclass Solution {}\n```"
        elif "c++" in q_low or "cpp" in q_low:
            return "Based on your saved knowledge, here is the C++ implementation:\n```cpp\nint main() {}\n```"
        elif "compare" in q_low:
            return "Based on your saved knowledge, both Java (`class Solution`) and C++ (`int main`) implementations are available."
        elif "origin" in q_low or "history" in q_low or "paper" in q_low:
            return "I couldn't find that information in your saved knowledge."
        else:
            return f"Based on your saved knowledge regarding {user_question}, Tarjan's algorithm uses DFS to find bridges in O(V + E) time."
