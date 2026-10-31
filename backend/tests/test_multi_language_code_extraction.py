import os
import zipfile
import pytest
from app.schemas import (
    IntermediateKnowledgeRepresentation,
    ExtractionPlan,
    IntentCategory,
    KnowledgeNode,
    CodeSnippet,
    SyntaxValidity,
    ObservationType
)
from app.services.artifact_service import ArtifactService
from app.services.project_service import project_service


def test_multi_language_code_extraction_separation(tmp_path):
    """
    Verifies that multiple code implementations (e.g. Java + C++) in the same project:
    1. Are saved into separate files in code/ (code/criticalConnections.java, code/criticalConnections.cpp).
    2. Are both included in manifest.json and export_package.zip.
    3. Are clearly labeled in the Markdown document.
    """
    service = ArtifactService()
    service.artifacts_base_dir = str(tmp_path)

    # 1. Create dummy project
    project = project_service.create_project(
        type('Req', (), {
            'source_url': 'https://youtu.be/qrAub5z8FeA',
            'user_prompt': 'Extract Java and C++ implementations'
        })
    )
    pid = project.project_id

    # 2. Construct IKR with Java and C++ snippets in the same topic node
    ikr = IntermediateKnowledgeRepresentation(
        project_id=pid,
        title="Multi-Language Test",
        intent_category=IntentCategory.CODE_EXTRACTION,
        topic_nodes=[
            KnowledgeNode(
                node_id="n1",
                topic_title="Critical Connections",
                concept_summary="Find bridges in graph using Tarjan's algorithm.",
                code_snippets=[
                    CodeSnippet(
                        filename="criticalConnections.java",
                        language="java",
                        code_content="public class Solution { public List<List<Integer>> criticalConnections(int n, List<List<Integer>> connections) {} }",
                        start_seconds=100.0,
                        end_seconds=110.0,
                        reconstruction_status=ObservationType.DIRECTLY_OBSERVED,
                        syntax_validity=SyntaxValidity.VERIFIED
                    ),
                    CodeSnippet(
                        filename="criticalConnections.cpp",
                        language="cpp",
                        code_content="class Solution { public: vector<vector<int>> criticalConnections(int n, vector<vector<int>>& connections) {} };",
                        start_seconds=120.0,
                        end_seconds=130.0,
                        reconstruction_status=ObservationType.DIRECTLY_OBSERVED,
                        syntax_validity=SyntaxValidity.VERIFIED
                    ),
                    CodeSnippet(
                        filename="snippet.txt",
                        language="LANGUAGE_UNCERTAIN",
                        code_content="pseudocode find_bridges(graph)",
                        start_seconds=140.0,
                        end_seconds=150.0,
                        reconstruction_status=ObservationType.RECONSTRUCTED,
                        syntax_validity=SyntaxValidity.UNVERIFIED_FRAGMENT
                    )
                ]
            )
        ]
    )

    from app.services.knowledge_reasoning_service import knowledge_reasoning_service
    knowledge_reasoning_service._knowledge_results[pid] = ikr

    # 3. Generate Artifacts
    res = service.generate_project_artifacts(pid)
    filenames = [a.filename for a in res.artifacts]

    assert "code/criticalConnections.java" in filenames
    assert "code/criticalConnections.cpp" in filenames
    assert "code/snippet.txt" in filenames

    # Verify Markdown preview content contains labels
    md = res.markdown_preview_content
    assert "JAVA: `criticalConnections.java`" in md
    assert "CPP: `criticalConnections.cpp`" in md
    assert "LANGUAGE_UNCERTAIN: `snippet.txt`" in md

    # Verify ZIP file contains all three files
    proj_dir = service.get_project_artifact_dir(pid)
    zip_path = os.path.join(proj_dir, "export_package.zip")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zip_names = zf.namelist()
        assert "code/criticalConnections.java" in zip_names
        assert "code/criticalConnections.cpp" in zip_names
        assert "code/snippet.txt" in zip_names
