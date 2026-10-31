import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import (
    ProjectCreateRequest,
    ProjectStatus,
    CollectionCreateRequest,
    IntermediateKnowledgeRepresentation,
    KnowledgeNode,
    CodeSnippet,
    EvidenceReference,
    ComplexityAnalysis,
    IntentCategory
)
from app.services.project_service import project_service
from app.services.library_service import library_service
from app.services.knowledge_reasoning_service import knowledge_reasoning_service
from app.services.conversation_service import conversation_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_chat_test_data():
    """Sets up deterministic test fixture dataset with 1 library item containing multi-language code and provenance."""
    owner = "chat_test_user"

    coll = library_service.create_collection(CollectionCreateRequest(name="Algorithms DSA", owner_id=owner))

    proj = project_service.create_project(ProjectCreateRequest(
        source_url="https://www.youtube.com/watch?v=tarjan123",
        user_prompt="Extract Tarjan graph code"
    ))
    project_service.update_status(proj.project_id, ProjectStatus.COMPLETED)

    ikr = IntermediateKnowledgeRepresentation(
        project_id=proj.project_id,
        title="Graph Algorithms — Tarjan's Algorithm",
        intent_category=IntentCategory.CODE_EXTRACTION,
        topic_nodes=[
            KnowledgeNode(
                node_id="n1",
                topic_title="Tarjan's Algorithm",
                concept_summary="Tarjan's algorithm identifies bridges and strongly connected components using DFS in O(V + E) time.",
                code_snippets=[
                    CodeSnippet(filename="Solution.java", language="java", code_content="class Solution { void tarjan() {} }", start_seconds=10, end_seconds=30),
                    CodeSnippet(filename="Solution.cpp", language="cpp", code_content="void tarjanBridge() {}", start_seconds=15, end_seconds=35)
                ],
                complexities=ComplexityAnalysis(
                    time_complexity="O(V + E)",
                    space_complexity="O(V)",
                    explanation="Queue and DFS recursion stack require O(V) space."
                ),
                evidence_references=[
                    EvidenceReference(evidence_id="e1", video_id="tarjan123", start_seconds=271.0, end_seconds=300.0, video_position=1)
                ]
            )
        ]
    )
    knowledge_reasoning_service._knowledge_results[proj.project_id] = ikr
    save_res = library_service.save_project_to_library(proj.project_id, coll.collection_id, owner_id=owner)

    return {"owner": owner, "item_id": save_res.knowledge_item_id, "coll_id": coll.collection_id}


def test_conversations_crud_operations(setup_chat_test_data):
    """Requirement 14, 16, 48: Create, list, retrieve, and delete conversation sessions."""
    owner = setup_chat_test_data["owner"]
    item_id = setup_chat_test_data["item_id"]

    # Create Conversation Session
    create_res = client.post("/api/conversations", json={
        "title": "Chat on Tarjan",
        "knowledge_item_id": item_id,
        "owner_id": owner
    })
    assert create_res.status_code == 201
    conv_data = create_res.json()
    c_id = conv_data["conversation_id"]

    # List Conversations
    list_res = client.get(f"/api/conversations?owner_id={owner}")
    assert list_res.status_code == 200
    assert any(c["conversation_id"] == c_id for c in list_res.json())

    # Get Conversation Details
    get_res = client.get(f"/api/conversations/{c_id}?owner_id={owner}")
    assert get_res.status_code == 200
    assert get_res.json()["conversation_id"] == c_id

    # Delete Conversation
    del_res = client.delete(f"/api/conversations/{c_id}?owner_id={owner}")
    assert del_res.status_code == 204


def test_grounded_chat_and_source_citations(setup_chat_test_data):
    """Requirement 3, 5, 12, 13, 56: Grounded Gemini generation with timestamped source citations."""
    owner = setup_chat_test_data["owner"]
    item_id = setup_chat_test_data["item_id"]

    conv = conversation_service.create_conversation(ConversationCreateRequest(
        knowledge_item_id=item_id,
        owner_id=owner
    ))

    # Post User Message: "What is the time complexity?"
    msg_res = client.post(f"/api/conversations/{conv.conversation_id}/messages", json={
        "content": "What is the time complexity?",
        "owner_id": owner
    })
    assert msg_res.status_code == 200
    msg_data = msg_res.json()
    assert msg_data["role"] == "assistant"
    assert "O(V + E)" in msg_data["content"]
    assert len(msg_data["sources"]) >= 1
    assert msg_data["sources"][0]["timestamp"] == "04:31"


def test_missing_knowledge_handling(setup_chat_test_data):
    """Requirement 6, 48, 56: Asking for absent information returns grounded 'not found' response."""
    owner = setup_chat_test_data["owner"]
    item_id = setup_chat_test_data["item_id"]

    conv = conversation_service.create_conversation(ConversationCreateRequest(
        knowledge_item_id=item_id,
        owner_id=owner
    ))

    # Post User Message: "What was the historical paper that introduced this algorithm?"
    msg_res = client.post(f"/api/conversations/{conv.conversation_id}/messages", json={
        "content": "What was the historical paper that introduced this algorithm?",
        "owner_id": owner
    })
    assert msg_res.status_code == 200
    msg_data = msg_res.json()
    assert "couldn't find that information" in msg_data["content"].lower() or "not found" in msg_data["content"].lower()


def test_code_aware_chat(setup_chat_test_data):
    """Requirement 10, 48, 56: Code-aware retrieval preserves Java vs C++ distinctions."""
    owner = setup_chat_test_data["owner"]
    item_id = setup_chat_test_data["item_id"]

    conv = conversation_service.create_conversation(ConversationCreateRequest(
        knowledge_item_id=item_id,
        owner_id=owner
    ))

    # Java request
    msg_java = client.post(f"/api/conversations/{conv.conversation_id}/messages", json={
        "content": "Show the Java implementation",
        "owner_id": owner
    })
    assert msg_java.status_code == 200
    assert "Java" in msg_java.json()["content"] or "class Solution" in msg_java.json()["content"]

    # C++ request
    msg_cpp = client.post(f"/api/conversations/{conv.conversation_id}/messages", json={
        "content": "Show the C++ implementation",
        "owner_id": owner
    })
    assert msg_cpp.status_code == 200
    assert "C++" in msg_cpp.json()["content"] or "main" in msg_cpp.json()["content"]


def test_ownership_isolation_chat(setup_chat_test_data):
    """Requirement 33, 48: Unauthorized user context cannot access conversation session."""
    owner = setup_chat_test_data["owner"]
    item_id = setup_chat_test_data["item_id"]

    conv = conversation_service.create_conversation(ConversationCreateRequest(
        knowledge_item_id=item_id,
        owner_id=owner
    ))

    # Unauthorized User B post message attempt -> 400 Access Denied
    res = client.post(f"/api/conversations/{conv.conversation_id}/messages", json={
        "content": "Hello",
        "owner_id": "unauthorized_user_B"
    })
    assert res.status_code == 400
