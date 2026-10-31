import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import (
    ProjectCreateRequest,
    ProjectStatus,
    CollectionCreateRequest,
    CollectionUpdateRequest,
    SaveToLibraryRequest,
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


def test_collections_crud_operations():
    """Requirement 16 & 26: Collection CRUD operations and ownership isolation."""
    # Create Collection
    create_res = client.post("/api/collections", json={
        "name": "System Design",
        "description": "Architecture patterns",
        "owner_id": "test_user_1"
    })
    assert create_res.status_code == 201
    coll_data = create_res.json()
    c_id = coll_data["collection_id"]
    assert coll_data["name"] == "System Design"

    # List Collections for owner
    list_res = client.get("/api/collections?owner_id=test_user_1")
    assert list_res.status_code == 200
    coll_list = list_res.json()
    assert any(c["collection_id"] == c_id for c in coll_list)

    # Get Collection by ID
    get_res = client.get(f"/api/collections/{c_id}?owner_id=test_user_1")
    assert get_res.status_code == 200
    assert get_res.json()["collection_id"] == c_id

    # Update Collection
    patch_res = client.patch(f"/api/collections/{c_id}?owner_id=test_user_1", json={
        "name": "Advanced System Design"
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Advanced System Design"

    # Safe Delete Collection
    del_res = client.delete(f"/api/collections/{c_id}?owner_id=test_user_1")
    assert del_res.status_code == 204


def test_save_project_to_library_and_duplicate_protection():
    """Requirement 15, 17, 26: Save completed project to collection with duplicate save protection."""
    # Create project and mark COMPLETED
    proj = project_service.create_project(ProjectCreateRequest(
        source_url="https://www.youtube.com/watch?v=qrAub5z8FeA",
        user_prompt="Extract graph code"
    ))
    project_service.update_status(proj.project_id, ProjectStatus.COMPLETED)

    # Register mock IKR in knowledge reasoning service
    node = KnowledgeNode(
        node_id="n1",
        topic_title="Graph Algorithms",
        concept_summary="BFS and Tarjan algorithm",
        code_snippets=[
            CodeSnippet(filename="Solution.java", language="java", code_content="class Solution {}", start_seconds=10, end_seconds=20),
            CodeSnippet(filename="Solution.cpp", language="cpp", code_content="int main() {}", start_seconds=15, end_seconds=25)
        ],
        evidence_references=[
            EvidenceReference(evidence_id="e1", video_id="qrAub5z8FeA", start_seconds=10.0, end_seconds=60.0, video_position=1)
        ]
    )
    ikr = IntermediateKnowledgeRepresentation(
        project_id=proj.project_id,
        title="Graph Algorithms",
        intent_category=IntentCategory.CODE_EXTRACTION,
        topic_nodes=[node]
    )
    knowledge_reasoning_service._knowledge_results[proj.project_id] = ikr

    # Create collection
    coll = library_service.create_collection(CollectionCreateRequest(name="Algorithms", owner_id="user_save_test"))

    # First Save
    save_res1 = client.post(f"/api/projects/{proj.project_id}/save-to-library", json={
        "collection_id": coll.collection_id,
        "owner_id": "user_save_test"
    })
    assert save_res1.status_code == 200
    save_data1 = save_res1.json()
    assert save_data1["status"] == "saved"
    item_id = save_data1["knowledge_item_id"]

    # Duplicate Save Protection (Second Save to same collection)
    save_res2 = client.post(f"/api/projects/{proj.project_id}/save-to-library", json={
        "collection_id": coll.collection_id,
        "owner_id": "user_save_test"
    })
    assert save_res2.status_code == 200
    save_data2 = save_res2.json()
    assert save_data2["status"] == "already_saved"
    assert save_data2["knowledge_item_id"] == item_id

    # Verify Provenance & Multi-Language Code Preservation in saved item
    item_res = client.get(f"/api/library/items/{item_id}?owner_id=user_save_test")
    assert item_res.status_code == 200
    item = item_res.json()
    assert item["project_id"] == proj.project_id
    assert "knowledge_snapshot" in item
    nodes = item["knowledge_snapshot"].get("topic_nodes", [])
    assert len(nodes) == 1
    code_languages = {cs["language"] for cs in nodes[0]["code_snippets"]}
    assert code_languages == {"java", "cpp"}
    ev_refs = nodes[0]["evidence_references"]
    assert len(ev_refs) == 1
    assert ev_refs[0]["video_id"] == "qrAub5z8FeA"


def test_save_incomplete_or_nonexistent_project_rejected():
    """Requirement 17 & 26: Saving incomplete or nonexistent projects is rejected with HTTP 400/404."""
    # Nonexistent project
    res1 = client.post("/api/projects/proj_nonexistent/save-to-library", json={"collection_id": "col_dsa"})
    assert res1.status_code == 400

    # Incomplete project (Status = PENDING)
    proj = project_service.create_project(ProjectCreateRequest(
        source_url="https://www.youtube.com/watch?v=qrAub5z8FeA",
        user_prompt="Extract code"
    ))
    res2 = client.post(f"/api/projects/{proj.project_id}/save-to-library", json={"collection_id": "col_dsa"})
    assert res2.status_code == 400
    assert "must be completed" in res2.json()["detail"]


def test_ownership_isolation_access_denied():
    """Requirement 19 & 26: Ownership isolation prevents unauthorized cross-user access."""
    coll = library_service.create_collection(CollectionCreateRequest(name="Private User A Notes", owner_id="user_A"))
    
    # User B attempts to access User A's collection -> 404 / Access Denied
    res = client.get(f"/api/collections/{coll.collection_id}?owner_id=user_B")
    assert res.status_code == 404
