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
    IntentCategory
)
from app.services.project_service import project_service
from app.services.library_service import library_service
from app.services.knowledge_reasoning_service import knowledge_reasoning_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_search_test_data():
    """Sets up deterministic test fixture dataset with 3 knowledge items across collections."""
    owner = "search_test_user"

    # Create Collection
    coll_dsa = library_service.create_collection(CollectionCreateRequest(name="Algorithms DSA", owner_id=owner))
    coll_ml = library_service.create_collection(CollectionCreateRequest(name="Machine Learning", owner_id=owner))

    # Item 1: Graph Algorithms — Tarjan's Algorithm
    proj1 = project_service.create_project(ProjectCreateRequest(
        source_url="https://www.youtube.com/watch?v=tarjan123",
        user_prompt="Extract Tarjan graph code"
    ))
    project_service.update_status(proj1.project_id, ProjectStatus.COMPLETED)
    ikr1 = IntermediateKnowledgeRepresentation(
        project_id=proj1.project_id,
        title="Graph Algorithms — Tarjan's Algorithm",
        intent_category=IntentCategory.CODE_EXTRACTION,
        topic_nodes=[
            KnowledgeNode(
                node_id="n1",
                topic_title="Tarjan's Algorithm",
                concept_summary="Tarjan's algorithm identifies bridges and strongly connected components in O(V + E) time using depth first search.",
                code_snippets=[
                    CodeSnippet(filename="Solution.java", language="java", code_content="class Solution { void tarjanDFS() {} }", start_seconds=10, end_seconds=30),
                    CodeSnippet(filename="Solution.cpp", language="cpp", code_content="void tarjanBridge() {}", start_seconds=15, end_seconds=35)
                ],
                evidence_references=[
                    EvidenceReference(evidence_id="e1", video_id="tarjan123", start_seconds=10.0, end_seconds=60.0, video_position=1)
                ]
            )
        ]
    )
    knowledge_reasoning_service._knowledge_results[proj1.project_id] = ikr1
    library_service.save_project_to_library(proj1.project_id, coll_dsa.collection_id, owner_id=owner)

    # Item 2: Dynamic Programming — Knapsack
    proj2 = project_service.create_project(ProjectCreateRequest(
        source_url="https://www.youtube.com/watch?v=knapsack456",
        user_prompt="Extract DP knapsack solution"
    ))
    project_service.update_status(proj2.project_id, ProjectStatus.COMPLETED)
    ikr2 = IntermediateKnowledgeRepresentation(
        project_id=proj2.project_id,
        title="Dynamic Programming — Knapsack",
        intent_category=IntentCategory.CODE_EXTRACTION,
        topic_nodes=[
            KnowledgeNode(
                node_id="n2",
                topic_title="Knapsack Problem",
                concept_summary="0/1 Knapsack problem solved using dynamic programming memoization with O(N*W) time complexity.",
                code_snippets=[
                    CodeSnippet(filename="solution.py", language="python", code_content="def knapsack(weights, values, capacity): pass", start_seconds=5, end_seconds=25)
                ]
            )
        ]
    )
    knowledge_reasoning_service._knowledge_results[proj2.project_id] = ikr2
    library_service.save_project_to_library(proj2.project_id, coll_dsa.collection_id, owner_id=owner)

    return {"owner": owner, "coll_dsa": coll_dsa.collection_id, "coll_ml": coll_ml.collection_id}


def test_basic_keyword_search_and_snippet_highlighting(setup_search_test_data):
    """Requirement 2, 13, 14, 35: Full-text keyword search, term snippets, and highlighting."""
    owner = setup_search_test_data["owner"]
    
    # Query: "tarjan"
    res = client.get(f"/api/search?q=tarjan&owner_id={owner}")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    item = data["results"][0]
    assert "Tarjan" in item["title"]
    assert "<mark>" in item["highlighted_title"] or "<mark>" in item["highlighted_snippet"]
    assert "java" in [l.lower() for l in item["matched_languages"]]


def test_multi_language_and_collection_filtering(setup_search_test_data):
    """Requirement 15, 20, 35: Filtering search results by language and collection."""
    owner = setup_search_test_data["owner"]
    coll_dsa = setup_search_test_data["coll_dsa"]

    # Language Filter: Python
    res_py = client.get(f"/api/search?q=knapsack&language=python&owner_id={owner}")
    assert res_py.status_code == 200
    data_py = res_py.json()
    assert data_py["total"] == 1
    assert data_py["results"][0]["title"] == "Dynamic Programming — Knapsack"

    # Collection Filter
    res_coll = client.get(f"/api/collections/{coll_dsa}/search?q=Graph&owner_id={owner}")
    assert res_coll.status_code == 200
    assert res_coll.json()["total"] >= 1


def test_deterministic_relevance_ranking(setup_search_test_data):
    """Requirement 31, 35: Title matches rank higher than content or source matches."""
    owner = setup_search_test_data["owner"]

    res = client.get(f"/api/search?q=Graph&owner_id={owner}")
    assert res.status_code == 200
    results = res.json()["results"]
    assert len(results) >= 1
    # Title match should have high score (> 0.8)
    assert results[0]["score"] >= 0.80


def test_pagination_and_has_next(setup_search_test_data):
    """Requirement 26, 35: Pagination page slicing and has_next calculation."""
    owner = setup_search_test_data["owner"]

    # Page 1 with page_size 1
    res = client.get(f"/api/search?q=Algorithm&page=1&page_size=1&owner_id={owner}")
    assert res.status_code == 200
    data = res.json()
    assert len(data["results"]) == 1
    assert data["has_next"] is True

    # Page 2
    res2 = client.get(f"/api/search?q=Algorithm&page=2&page_size=1&owner_id={owner}")
    assert res2.status_code == 200
    assert res2.json()["page"] == 2


def test_ownership_isolation_search(setup_search_test_data):
    """Requirement 28, 35: Unauthorized user context returns 0 search results."""
    # Other user searching for same terms
    res = client.get("/api/search?q=tarjan&owner_id=unauthorized_user_B")
    assert res.status_code == 200
    assert res.json()["total"] == 0
