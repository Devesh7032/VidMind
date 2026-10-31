import os
import json
import zipfile
import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import (
    ExtractionPlan,
    IntentCategory,
    ContentType,
    ArtifactType,
    IntermediateKnowledgeRepresentation,
    KnowledgeNode,
    CodeSnippet,
    ComplexityAnalysis,
    EvidenceReference,
    ObservationType,
    SyntaxValidity
)
from app.services.artifact_service import artifact_service
from app.services.knowledge_reasoning_service import knowledge_reasoning_service

client = TestClient(app)


def test_filename_sanitization_and_path_traversal_prevention():
    sanitized = artifact_service.sanitize_filename("../../../etc/passwd")
    assert ".." not in sanitized
    assert "/" not in sanitized
    assert "\\" not in sanitized
    assert sanitized == "passwd"

    sanitized_code = artifact_service.sanitize_filename("my_code/../../bfs.py")
    assert ".." not in sanitized_code
    assert sanitized_code == "bfs.py"


def test_markdown_generation_for_code_extraction():
    proj_res = client.post("/api/projects", json={
        "source_url": "https://www.youtube.com/watch?v=md_test_vid",
        "user_prompt": "Extract BFS code and complexity."
    })
    project_id = proj_res.json()["project_id"]

    ikr = knowledge_reasoning_service.construct_intermediate_knowledge_representation(project_id)
    plan = ExtractionPlan(intent_category=IntentCategory.CODE_EXTRACTION, content_types=[ContentType.CODE])

    md_text = artifact_service.generate_markdown_content(ikr, plan)
    assert "# " in md_text
    assert "Breadth-First Search" in md_text
    assert "```" in md_text
    assert "Time Complexity" in md_text
    assert "Source Timestamp" in md_text


def test_language_extension_and_comments():
    fname, ext, comment = artifact_service._get_language_extension_and_comment("cpp", "critical_connections.cpp")
    assert ext == ".cpp"
    assert comment == "//"
    assert fname == "critical_connections.cpp"

    fname_java, ext_java, comment_java = artifact_service._get_language_extension_and_comment("java", "Solution.java")
    assert ext_java == ".java"
    assert comment_java == "//"

    fname_py, ext_py, comment_py = artifact_service._get_language_extension_and_comment("python", "main")
    assert ext_py == ".py"
    assert comment_py == "#"


def test_missing_optional_ikr_fields_handling():
    ikr_minimal = IntermediateKnowledgeRepresentation(
        project_id="test_minimal",
        title="Minimal Video",
        intent_category=IntentCategory.CODE_EXTRACTION,
        topic_nodes=[
            KnowledgeNode(
                node_id="node_min",
                topic_title="Minimal Topic",
                concept_summary="Summary text",
                code_snippets=[
                    CodeSnippet(
                        filename=None,
                        language="cpp",
                        code_content="int main() { return 0; }",
                        start_seconds=0.0,
                        end_seconds=10.0
                    )
                ],
                complexities=None,
                evidence_references=[]
            )
        ]
    )
    plan = ExtractionPlan(intent_category=IntentCategory.CODE_EXTRACTION)
    md = artifact_service.generate_markdown_content(ikr_minimal, plan)
    assert "Minimal Topic" in md
    assert "int main()" in md


def test_artifact_packaging_code_manifest_zip():
    proj_res = client.post("/api/projects", json={
        "source_url": "https://www.youtube.com/watch?v=pkg_test_vid",
        "user_prompt": "Extract BFS code and revision notes."
    })
    project_id = proj_res.json()["project_id"]

    res = artifact_service.generate_project_artifacts(project_id)
    assert res.project_id == project_id
    assert res.total_artifacts >= 3
    assert res.markdown_preview_content is not None

    proj_dir = artifact_service.get_project_artifact_dir(project_id)
    md_file = os.path.join(proj_dir, "knowledge_pack.md")
    manifest_file = os.path.join(proj_dir, "manifest.json")
    zip_file = os.path.join(proj_dir, "export_package.zip")
    code_file = os.path.join(proj_dir, "code", "bfs.py")

    assert os.path.exists(md_file)
    assert os.path.exists(manifest_file)
    assert os.path.exists(zip_file)
    assert os.path.exists(code_file)

    # Manifest json integrity
    with open(manifest_file, "r") as f:
        manifest_data = json.load(f)
    assert manifest_data["project_id"] == project_id
    assert "generated_files" in manifest_data

    # ZIP package integrity
    with zipfile.ZipFile(zip_file, "r") as zf:
        namelist = zf.namelist()
        assert "knowledge_pack.md" in namelist
        assert "manifest.json" in namelist
        assert "code/bfs.py" in namelist


def test_api_list_artifacts_and_download_endpoints():
    proj_res = client.post("/api/projects", json={
        "source_url": "https://www.youtube.com/watch?v=api_download_test",
        "user_prompt": "Extract BFS code."
    })
    project_id = proj_res.json()["project_id"]

    job_res = client.post(f"/api/projects/{project_id}/analyze")
    job_id = job_res.json()["job_id"]

    max_wait = 4.0
    start_t = time.time()
    while time.time() - start_t < max_wait:
        res = client.get(f"/api/jobs/{job_id}")
        if res.json()["status"] == "COMPLETED":
            break
        time.sleep(0.1)

    # List artifacts API
    list_res = client.get(f"/api/projects/{project_id}/artifacts")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total_artifacts"] >= 3

    # Download ZIP artifact API
    zip_art = [a for a in list_data["artifacts"] if a["artifact_type"] == "ZIP_PROJECT"][0]
    dl_res = client.get(zip_art["download_url"])
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/zip"
    assert len(dl_res.content) > 0


def test_full_end_to_end_mvp1_pipeline():
    """
    End-to-End Test for Complete MVP-1 Flow:
    URL + Prompt -> Project -> Job -> Ingestion -> Intent -> Fusion -> Knowledge -> Markdown + Code + ZIP
    """
    proj_res = client.post("/api/projects", json={
        "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "user_prompt": "Extract the main BFS algorithm, code, explanation, time complexity and space complexity and create revision notes."
    })
    assert proj_res.status_code == 201
    project_id = proj_res.json()["project_id"]

    job_res = client.post(f"/api/projects/{project_id}/analyze")
    assert job_res.status_code == 202
    job_id = job_res.json()["job_id"]

    max_wait = 5.0
    start_t = time.time()
    final_job = None
    while time.time() - start_t < max_wait:
        res = client.get(f"/api/jobs/{job_id}")
        data = res.json()
        if data["status"] in ["COMPLETED", "FAILED"]:
            final_job = data
            break
        time.sleep(0.1)

    assert final_job is not None
    assert final_job["status"] == "COMPLETED"
    assert final_job["progress_percent"] == 100

    # Verify final artifacts
    list_res = client.get(f"/api/projects/{project_id}/artifacts")
    assert list_res.status_code == 200
    artifacts_data = list_res.json()
    assert artifacts_data["total_artifacts"] >= 3
    assert "Breadth-First Search" in artifacts_data["markdown_preview_content"]
