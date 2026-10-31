import os
import tempfile
import pytest
from app.schemas import (
    ProjectCreateRequest,
    IntermediateKnowledgeRepresentation,
    ExtractionPlan,
    KnowledgeNode,
    CodeSnippet,
    SyntaxValidity,
    ObservationType,
    IntentCategory,
    PlaylistMetadataResponse,
    PlaylistVideoItem
)
from app.services.project_service import project_service
from app.services.knowledge_reasoning_service import knowledge_reasoning_service
from app.services.artifact_service import artifact_service


def test_single_video_code_extraction_behavior_unchanged():
    """Verify SINGLE VIDEO code extraction behavior remains 100% unchanged (Solution.java, Solution.cpp, etc.)."""
    req = ProjectCreateRequest(
        source_url="https://www.youtube.com/watch?v=single_vid_test_123",
        user_prompt="Extract Java and C++ code"
    )
    proj = project_service.create_project(req)
    assert proj.is_playlist is False

    ikr = IntermediateKnowledgeRepresentation(
        project_id=proj.project_id,
        title="Single Video Title",
        intent_category=IntentCategory.CODE_EXTRACTION,
        topic_nodes=[
            KnowledgeNode(
                node_id="n1",
                topic_title="Graph BFS",
                concept_summary="Single video BFS snippet",
                code_snippets=[
                    CodeSnippet(
                        filename="Solution.java",
                        language="java",
                        code_content="public class Solution { public static void main(String[] args) {} }",
                        start_seconds=10.0,
                        end_seconds=45.0
                    ),
                    CodeSnippet(
                        filename="Solution.cpp",
                        language="cpp",
                        code_content="int main() { return 0; }",
                        start_seconds=50.0,
                        end_seconds=90.0
                    )
                ]
            )
        ]
    )

    knowledge_reasoning_service._knowledge_results[proj.project_id] = ikr
    res = artifact_service.generate_project_artifacts(proj.project_id)

    filenames = [a.filename for a in res.artifacts]
    assert "code/Solution.java" in filenames
    assert "code/Solution.cpp" in filenames
    assert "code/playlist_java.md" not in filenames


def test_playlist_java_and_cpp_consolidation():
    """Verify PLAYLIST consolidates Java into playlist_java.md and C++ into playlist_cpp.md grouped by Video."""
    req = ProjectCreateRequest(
        source_url="https://www.youtube.com/playlist?list=PL_test_java_cpp",
        user_prompt="Extract Java and C++ code"
    )
    proj = project_service.create_project(req)
    assert proj.is_playlist is True

    # Setup 2 playlist video items
    pl_meta = PlaylistMetadataResponse(
        playlist_id=f"pl_{proj.project_id}",
        source_url=proj.source_url,
        title="Java & C++ DSA Course",
        total_videos=2,
        videos=[
            PlaylistVideoItem(
                video_id="v1_id",
                source_url="https://www.youtube.com/watch?v=v1_id",
                title="Graph Traversal",
                position=1
            ),
            PlaylistVideoItem(
                video_id="v2_id",
                source_url="https://www.youtube.com/watch?v=v2_id",
                title="Shortest Path",
                position=2
            )
        ]
    )
    proj.playlist_metadata = pl_meta

    # Child 1 IKR
    child_pid_1 = f"{proj.project_id}_v1"
    ikr_1 = IntermediateKnowledgeRepresentation(
        project_id=child_pid_1,
        title="Graph Traversal",
        intent_category=IntentCategory.CODE_EXTRACTION,
        topic_nodes=[
            KnowledgeNode(
                node_id="n1",
                topic_title="BFS",
                concept_summary="Java BFS code",
                code_snippets=[
                    CodeSnippet(
                        filename="BFS.java",
                        language="java",
                        code_content="public void bfs() { System.out.println(\"BFS\"); }",
                        start_seconds=10.0,
                        end_seconds=45.0
                    ),
                    CodeSnippet(
                        filename="BFS.cpp",
                        language="cpp",
                        code_content="void bfs() { std::cout << \"BFS\"; }",
                        start_seconds=50.0,
                        end_seconds=90.0
                    )
                ]
            )
        ]
    )
    knowledge_reasoning_service._knowledge_results[child_pid_1] = ikr_1

    # Child 2 IKR
    child_pid_2 = f"{proj.project_id}_v2"
    ikr_2 = IntermediateKnowledgeRepresentation(
        project_id=child_pid_2,
        title="Shortest Path",
        intent_category=IntentCategory.CODE_EXTRACTION,
        topic_nodes=[
            KnowledgeNode(
                node_id="n2",
                topic_title="Dijkstra",
                concept_summary="Java Dijkstra code",
                code_snippets=[
                    CodeSnippet(
                        filename="Dijkstra.java",
                        language="java",
                        code_content="public void dijkstra() { System.out.println(\"Dijkstra\"); }",
                        start_seconds=15.0,
                        end_seconds=80.0
                    )
                ]
            )
        ]
    )
    knowledge_reasoning_service._knowledge_results[child_pid_2] = ikr_2

    # Main Playlist IKR
    main_ikr = IntermediateKnowledgeRepresentation(
        project_id=proj.project_id,
        title="Java & C++ DSA Course",
        intent_category=IntentCategory.CODE_EXTRACTION,
        topic_nodes=[]
    )
    knowledge_reasoning_service._knowledge_results[proj.project_id] = main_ikr

    res = artifact_service.generate_project_artifacts(proj.project_id)
    filenames = [a.filename for a in res.artifacts]

    assert "code/playlist_java.md" in filenames
    assert "code/playlist_cpp.md" in filenames
    assert "code/Solution.java" not in filenames

    # Check contents of playlist_java.md
    java_art = next(a for a in res.artifacts if a.filename == "code/playlist_java.md")
    path, _ = artifact_service.get_artifact_file_path(java_art.artifact_id)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "# Java Code — Playlist" in content
    assert "## Video 1 — Graph Traversal" in content
    assert "Source: https://www.youtube.com/watch?v=v1_id" in content
    assert "Timestamp: 10.0s - 45.0s" in content
    assert "### Java Code" in content
    assert "public void bfs()" in content
    assert "## Video 2 — Shortest Path" in content
    assert "public void dijkstra()" in content


def test_playlist_only_java_code_no_empty_cpp_file():
    """Verify PLAYLIST with ONLY Java code produces code/playlist_java.md and NO empty code/playlist_cpp.md."""
    req = ProjectCreateRequest(
        source_url="https://www.youtube.com/playlist?list=PL_test_java_only",
        user_prompt="Extract Java code"
    )
    proj = project_service.create_project(req)
    assert proj.is_playlist is True

    pl_meta = PlaylistMetadataResponse(
        playlist_id=f"pl_{proj.project_id}",
        source_url=proj.source_url,
        title="Java Course",
        total_videos=1,
        videos=[
            PlaylistVideoItem(
                video_id="v1_java_only",
                source_url="https://www.youtube.com/watch?v=v1_java_only",
                title="Intro to Java",
                position=1
            )
        ]
    )
    proj.playlist_metadata = pl_meta

    child_pid_1 = f"{proj.project_id}_v1"
    ikr_1 = IntermediateKnowledgeRepresentation(
        project_id=child_pid_1,
        title="Intro to Java",
        intent_category=IntentCategory.CODE_EXTRACTION,
        topic_nodes=[
            KnowledgeNode(
                node_id="n1",
                topic_title="Java Hello World",
                concept_summary="Java intro snippet",
                code_snippets=[
                    CodeSnippet(
                        filename="Main.java",
                        language="java",
                        code_content="public class Main { public static void main(String[] args) {} }",
                        start_seconds=5.0,
                        end_seconds=25.0
                    )
                ]
            )
        ]
    )
    knowledge_reasoning_service._knowledge_results[child_pid_1] = ikr_1

    main_ikr = IntermediateKnowledgeRepresentation(
        project_id=proj.project_id,
        title="Java Course",
        intent_category=IntentCategory.CODE_EXTRACTION,
        topic_nodes=[]
    )
    knowledge_reasoning_service._knowledge_results[proj.project_id] = main_ikr

    res = artifact_service.generate_project_artifacts(proj.project_id)
    filenames = [a.filename for a in res.artifacts]

    assert "code/playlist_java.md" in filenames
    assert "code/playlist_cpp.md" not in filenames
    assert "code/playlist_py.md" not in filenames
