import os
import zipfile
import json
import csv
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
from app.services.export_service import export_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_export_test_data():
    """Sets up deterministic test fixture dataset with 1 library item containing multi-language code and provenance."""
    owner = "export_test_user"

    coll = library_service.create_collection(CollectionCreateRequest(name="Export DSA Collection", owner_id=owner))

    proj = project_service.create_project(ProjectCreateRequest(
        source_url="https://www.youtube.com/watch?v=tarjan999",
        user_prompt="Extract Tarjan graph algorithms"
    ))
    project_service.update_status(proj.project_id, ProjectStatus.COMPLETED)

    ikr = IntermediateKnowledgeRepresentation(
        project_id=proj.project_id,
        title="Graph Algorithms — Tarjan's Algorithm",
        intent_category=IntentCategory.CODE_EXTRACTION,
        topic_nodes=[
            KnowledgeNode(
                node_id="n100",
                topic_title="Tarjan's Bridge Finding Algorithm",
                concept_summary="Tarjan's algorithm identifies bridges using DFS in O(V + E) time.",
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
                    EvidenceReference(evidence_id="ev_tarjan", video_id="tarjan999", start_seconds=271.0, end_seconds=300.0, video_position=1)
                ]
            )
        ]
    )
    knowledge_reasoning_service._knowledge_results[proj.project_id] = ikr
    save_res = library_service.save_project_to_library(proj.project_id, coll.collection_id, owner_id=owner)

    return {"owner": owner, "item_id": save_res.knowledge_item_id, "coll_id": coll.collection_id}


def test_markdown_export(setup_export_test_data):
    """Requirement 8, 9, 10, 49, 55: Markdown export preserves topics, complexities, multi-language code, timestamps."""
    owner = setup_export_test_data["owner"]
    item_id = setup_export_test_data["item_id"]

    res = client.get(f"/api/library/items/{item_id}/export/markdown?owner_id={owner}")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/markdown")
    
    text = res.text
    assert "Graph Algorithms — Tarjan's Algorithm" in text
    assert "Tarjan's Bridge Finding Algorithm" in text
    assert "O(V + E)" in text
    assert "Solution.java" in text
    assert "Solution.cpp" in text
    assert "04:31" in text or "271.0s" in text


def test_json_export(setup_export_test_data):
    """Requirement 14, 15, 16, 52: Machine-readable JSON export with schema_version 1.0."""
    owner = setup_export_test_data["owner"]
    item_id = setup_export_test_data["item_id"]

    res = client.get(f"/api/library/items/{item_id}/export/json?owner_id={owner}")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/json")

    data = res.json()
    assert data["schema_version"] == "1.0"
    assert data["package_type"] == "vidmind_knowledge_json"
    assert data["knowledge_item"]["title"] == "Graph Algorithms — Tarjan's Algorithm"
    assert len(data["knowledge_snapshot"]["canonical_nodes"]) >= 1


def test_pdf_export(setup_export_test_data):
    """Requirement 11, 50: PDF export produces valid readable PDF document."""
    owner = setup_export_test_data["owner"]
    item_id = setup_export_test_data["item_id"]

    res = client.get(f"/api/library/items/{item_id}/export/pdf?owner_id={owner}")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/pdf")
    assert len(res.content) > 100


def test_anki_export(setup_export_test_data):
    """Requirement 17, 18, 53: Anki CSV export with Front, Back, Tags headers."""
    owner = setup_export_test_data["owner"]
    item_id = setup_export_test_data["item_id"]

    res = client.get(f"/api/library/items/{item_id}/export/anki?owner_id={owner}")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")

    lines = res.text.splitlines()
    assert len(lines) >= 2
    assert "Front,Back,Tags" in lines[0] or '"Front","Back","Tags"' in lines[0]


def test_complete_zip_package_export(setup_export_test_data):
    """Requirement 19, 20, 21, 22, 54, 66: ZIP package contains README, manifest with sha256 hashes, notes, code, and flashcards."""
    owner = setup_export_test_data["owner"]
    item_id = setup_export_test_data["item_id"]

    res = client.get(f"/api/library/items/{item_id}/export/zip?owner_id={owner}")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/zip")

    zip_bytes = res.content
    item_dir = export_service._get_item_dir(item_id)
    temp_zip_path = os.path.join(item_dir, "test_verify.zip")
    with open(temp_zip_path, "wb") as f:
        f.write(zip_bytes)

    assert zipfile.is_zipfile(temp_zip_path)
    with zipfile.ZipFile(temp_zip_path, "r") as zf:
        namelist = zf.namelist()
        assert "README.md" in namelist
        assert "manifest.json" in namelist
        assert "knowledge.json" in namelist
        assert "notes/knowledge.md" in namelist
        assert "flashcards/anki.csv" in namelist
        assert any(n.startswith("code/") for n in namelist)

        manifest_content = zf.read("manifest.json").decode("utf-8")
        manifest_json = json.loads(manifest_content)
        assert manifest_json["schema_version"] == "1.0"
        assert len(manifest_json["files"]) >= 4
        assert "sha256" in manifest_json["files"][0]


def test_export_security_no_secrets_and_ownership(setup_export_test_data):
    """Requirement 26, 40, 41, 58: No secret API keys in exports and unauthorized access denied."""
    owner = setup_export_test_data["owner"]
    item_id = setup_export_test_data["item_id"]

    # 1. Secret Exclusion Check
    res_md = client.get(f"/api/library/items/{item_id}/export/markdown?owner_id={owner}")
    assert "GEMINI_API_KEY" not in res_md.text

    # 2. Ownership Isolation Check (Unauthorized user B -> 404 Access Denied)
    res_unauth = client.get(f"/api/library/items/{item_id}/export/zip?owner_id=unauthorized_user_B")
    assert res_unauth.status_code == 404
