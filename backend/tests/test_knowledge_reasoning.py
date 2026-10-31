import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import (
    ExtractionPlan,
    IntentCategory,
    ContentType,
    ObservationType,
    SyntaxValidity,
    IntermediateKnowledgeRepresentation
)
from app.services.knowledge_reasoning_service import knowledge_reasoning_service
from app.services.ai.mock_provider import MockLLMProvider
from app.services.ai.base import LLMProviderInterface

client = TestClient(app)


def test_code_knowledge_extraction_and_ast_validation():
    provider = MockLLMProvider()
    plan = ExtractionPlan(
        intent_category=IntentCategory.CODE_EXTRACTION,
        content_types=[ContentType.CODE, ContentType.TIME_COMPLEXITY]
    )
    ikr = provider.reason_knowledge_graph(
        project_id="test_proj_code",
        plan=plan,
        evidence_list=[],
        project_title="DSA Tutorial"
    )

    assert isinstance(ikr, IntermediateKnowledgeRepresentation)
    assert len(ikr.topic_nodes) > 0
    node = ikr.topic_nodes[0]
    assert "BFS" in node.topic_title
    assert len(node.code_snippets) > 0
    snippet = node.code_snippets[0]
    assert snippet.language == "python"
    assert snippet.syntax_validity == SyntaxValidity.VERIFIED
    assert node.complexities is not None
    assert node.complexities.time_complexity == "O(V + E)"


def test_formula_knowledge_extraction():
    provider = MockLLMProvider()
    plan = ExtractionPlan(
        intent_category=IntentCategory.FORMULA_SHEET,
        content_types=[ContentType.FORMULAS]
    )
    ikr = provider.reason_knowledge_graph("test_proj_formula", plan, [], "Math Lecture")
    node = ikr.topic_nodes[0]
    assert len(node.formulas) > 0
    assert "O(V + E)" in node.formulas[0]


def test_interview_prep_qna_extraction():
    provider = MockLLMProvider()
    plan = ExtractionPlan(
        intent_category=IntentCategory.INTERVIEW_PREP,
        content_types=[ContentType.QUESTIONS_ANSWERS]
    )
    ikr = provider.reason_knowledge_graph("test_proj_qna", plan, [], "Interview Prep Video")
    node = ikr.topic_nodes[0]
    assert len(node.questions_and_answers) > 0
    assert "question" in node.questions_and_answers[0]
    assert "answer" in node.questions_and_answers[0]


def test_observation_type_classification():
    provider = MockLLMProvider()
    plan = ExtractionPlan(intent_category=IntentCategory.STUDY_NOTES)
    ikr = provider.reason_knowledge_graph("test_proj_obs", plan, [], "Study Notes Video")
    node = ikr.topic_nodes[0]
    assert node.observation_type in [ObservationType.DIRECTLY_OBSERVED, ObservationType.RECONSTRUCTED, ObservationType.AI_INFERRED]


def test_syntax_validation_failure_handling():
    provider = MockLLMProvider()
    invalid_code = "def broken_func(: bad syntax"
    syntax_status = provider._validate_python_syntax(invalid_code)
    assert syntax_status == SyntaxValidity.SYNTAX_ERROR


def test_faulty_provider_fallback_handling():
    class FaultyReasoningProvider(MockLLMProvider):
        def reason_knowledge_graph(self, project_id, plan, evidence_list, project_title="Video Knowledge"):
            raise RuntimeError("LLM Reasoning Service Exception")

    from app.services.ai.intent_engine import intent_engine
    old_provider = intent_engine.get_provider()
    try:
        intent_engine.set_provider(FaultyReasoningProvider())
        proj_res = client.post("/api/projects", json={
            "source_url": "https://www.youtube.com/watch?v=faulty_reasoning_test",
            "user_prompt": "Extract code and revision notes."
        })
        project_id = proj_res.json()["project_id"]

        # Construction falls back cleanly to MockLLMProvider
        ikr = knowledge_reasoning_service.construct_intermediate_knowledge_representation(project_id)
        assert ikr.project_id == project_id
        assert len(ikr.topic_nodes) > 0
    finally:
        intent_engine.set_provider(old_provider)


def test_end_to_end_knowledge_reasoning_job_pipeline():
    proj_res = client.post("/api/projects", json={
        "source_url": "https://www.youtube.com/watch?v=ikr_pipeline_vid",
        "user_prompt": "Extract the main BFS algorithm, code, explanation and time complexity."
    })
    project_id = proj_res.json()["project_id"]

    job_res = client.post(f"/api/projects/{project_id}/analyze")
    assert job_res.status_code == 202
    job_id = job_res.json()["job_id"]

    # Poll status until job reaches KNOWLEDGE_READY
    max_wait = 4.0
    start_t = time.time()
    final_job = None

    while time.time() - start_t < max_wait:
        res = client.get(f"/api/jobs/{job_id}")
        data = res.json()
        if data["status"] in ["KNOWLEDGE_READY", "COMPLETED", "FAILED"]:
            final_job = data
            break
        time.sleep(0.1)

    assert final_job is not None
    assert final_job["status"] == "KNOWLEDGE_READY"
    assert final_job["progress_percent"] == 100

    # Fetch knowledge API endpoint
    know_res = client.get(f"/api/projects/{project_id}/knowledge")
    assert know_res.status_code == 200
    know_data = know_res.json()
    assert know_data["project_id"] == project_id
    assert len(know_data["topic_nodes"]) > 0
    assert "Breadth-First Search" in know_data["topic_nodes"][0]["topic_title"]
