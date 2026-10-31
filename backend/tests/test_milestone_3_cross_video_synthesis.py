import pytest
from app.schemas import (
    IntermediateKnowledgeRepresentation,
    KnowledgeNode,
    EvidenceReference,
    CodeSnippet,
    ComplexityAnalysis,
    ObservationType,
    IntentCategory,
    RelationshipType
)
from app.services.cross_video_synthesis_service import cross_video_synthesis_engine


def test_required_fixture_bfs_dfs_deduplication_and_separation():
    """Requirement 32: Required Test Fixture (BFS & Breadth First Search merge into BFS; DFS remains separate)."""
    # Video 1: "Introduction to BFS"
    node_v1 = KnowledgeNode(
        node_id="n1",
        topic_title="Introduction to BFS",
        concept_summary="BFS explores nodes level by level.",
        evidence_references=[
            EvidenceReference(evidence_id="e1", video_id="vid_1", start_seconds=10.0, end_seconds=60.0, video_position=1)
        ]
    )

    # Video 2: "BFS Implementation"
    node_v2 = KnowledgeNode(
        node_id="n2",
        topic_title="BFS Implementation",
        concept_summary="BFS uses a queue.",
        evidence_references=[
            EvidenceReference(evidence_id="e2", video_id="vid_2", start_seconds=20.0, end_seconds=100.0, video_position=2)
        ]
    )

    # Video 3: "DFS"
    node_v3 = KnowledgeNode(
        node_id="n3",
        topic_title="DFS",
        concept_summary="Depth First Search uses recursion or a stack.",
        evidence_references=[
            EvidenceReference(evidence_id="e3", video_id="vid_3", start_seconds=5.0, end_seconds=50.0, video_position=3)
        ]
    )

    # Video 4: "Breadth First Search Advanced"
    node_v4 = KnowledgeNode(
        node_id="n4",
        topic_title="Breadth First Search Advanced",
        concept_summary="BFS shortest path on unweighted graphs.",
        evidence_references=[
            EvidenceReference(evidence_id="e4", video_id="vid_4", start_seconds=15.0, end_seconds=80.0, video_position=4)
        ]
    )

    ikr1 = IntermediateKnowledgeRepresentation(project_id="p1", title="V1", intent_category=IntentCategory.STUDY_NOTES, topic_nodes=[node_v1])
    ikr2 = IntermediateKnowledgeRepresentation(project_id="p2", title="V2", intent_category=IntentCategory.STUDY_NOTES, topic_nodes=[node_v2])
    ikr3 = IntermediateKnowledgeRepresentation(project_id="p3", title="V3", intent_category=IntentCategory.STUDY_NOTES, topic_nodes=[node_v3])
    ikr4 = IntermediateKnowledgeRepresentation(project_id="p4", title="V4", intent_category=IntentCategory.STUDY_NOTES, topic_nodes=[node_v4])

    video_ikrs = [(1, ikr1), (2, ikr2), (3, ikr3), (4, ikr4)]

    graph = cross_video_synthesis_engine.synthesize_playlist_knowledge(
        project_id="proj_pl1",
        playlist_id="pl_123",
        playlist_title="Graph Algorithms",
        video_ikrs=video_ikrs
    )

    canonical_titles = [n.topic_title for n in graph.canonical_nodes]
    assert "BFS" in canonical_titles
    assert "DFS" in canonical_titles
    assert len(graph.canonical_nodes) == 2  # BFS and DFS

    # Verify BFS evidence preservation across Video 1, Video 2, Video 4
    bfs_node = next(n for n in graph.canonical_nodes if n.topic_title == "BFS")
    assert len(bfs_node.evidence_references) == 3
    video_positions = {ev.video_position for ev in bfs_node.evidence_references}
    assert video_positions == {1, 2, 4}


def test_multi_language_fixture_association():
    """Requirement 33: Multi-language test fixture (BFS Java, BFS C++, BFS Python associate under one BFS topic)."""
    code_java = CodeSnippet(filename="Solution.java", language="java", code_content="class Solution {}", start_seconds=10, end_seconds=20)
    code_cpp = CodeSnippet(filename="Solution.cpp", language="cpp", code_content="int main() {}", start_seconds=15, end_seconds=25)
    code_py = CodeSnippet(filename="solution.py", language="python", code_content="def bfs(): pass", start_seconds=5, end_seconds=15)

    node_v1 = KnowledgeNode(node_id="n1", topic_title="BFS Java", concept_summary="BFS in Java", code_snippets=[code_java], evidence_references=[EvidenceReference(evidence_id="e1", video_id="v1", start_seconds=0, end_seconds=30, video_position=1)])
    node_v2 = KnowledgeNode(node_id="n2", topic_title="BFS C++", concept_summary="BFS in C++", code_snippets=[code_cpp], evidence_references=[EvidenceReference(evidence_id="e2", video_id="v2", start_seconds=0, end_seconds=30, video_position=2)])
    node_v3 = KnowledgeNode(node_id="n3", topic_title="BFS Python", concept_summary="BFS in Python", code_snippets=[code_py], evidence_references=[EvidenceReference(evidence_id="e3", video_id="v3", start_seconds=0, end_seconds=30, video_position=3)])

    video_ikrs = [
        (1, IntermediateKnowledgeRepresentation(project_id="p1", title="V1", intent_category=IntentCategory.CODE_EXTRACTION, topic_nodes=[node_v1])),
        (2, IntermediateKnowledgeRepresentation(project_id="p2", title="V2", intent_category=IntentCategory.CODE_EXTRACTION, topic_nodes=[node_v2])),
        (3, IntermediateKnowledgeRepresentation(project_id="p3", title="V3", intent_category=IntentCategory.CODE_EXTRACTION, topic_nodes=[node_v3]))
    ]

    graph = cross_video_synthesis_engine.synthesize_playlist_knowledge(
        project_id="proj_pl2",
        playlist_id="pl_456",
        playlist_title="Multi-Language BFS",
        video_ikrs=video_ikrs
    )

    assert len(graph.canonical_nodes) == 1
    bfs_node = graph.canonical_nodes[0]
    assert bfs_node.topic_title == "BFS"
    assert len(bfs_node.code_snippets) == 3
    languages = {cs.language for cs in bfs_node.code_snippets}
    assert languages == {"java", "cpp", "python"}


def test_over_merge_protection():
    """Requirement 3: Over-merge protection ensures BFS/DFS and Dijkstra/Bellman-Ford remain separate."""
    n1 = KnowledgeNode(node_id="n1", topic_title="Dijkstra", concept_summary="Dijkstra shortest path", evidence_references=[EvidenceReference(evidence_id="e1", video_id="v1", start_seconds=0, end_seconds=10, video_position=1)])
    n2 = KnowledgeNode(node_id="n2", topic_title="Bellman-Ford", concept_summary="Bellman-Ford negative edges", evidence_references=[EvidenceReference(evidence_id="e2", video_id="v2", start_seconds=0, end_seconds=10, video_position=2)])

    video_ikrs = [
        (1, IntermediateKnowledgeRepresentation(project_id="p1", title="V1", intent_category=IntentCategory.STUDY_NOTES, topic_nodes=[n1])),
        (2, IntermediateKnowledgeRepresentation(project_id="p2", title="V2", intent_category=IntentCategory.STUDY_NOTES, topic_nodes=[n2]))
    ]

    graph = cross_video_synthesis_engine.synthesize_playlist_knowledge(
        project_id="proj_pl3",
        playlist_id="pl_789",
        playlist_title="Shortest Path Algorithms",
        video_ikrs=video_ikrs
    )

    assert len(graph.canonical_nodes) == 2
    titles = [n.topic_title for n in graph.canonical_nodes]
    assert "Dijkstra" in titles
    assert "Bellman-Ford" in titles


def test_complexity_variant_and_conflict_handling():
    """Requirement 18: Conflicting complexity statements across videos are registered as KnowledgeVariant records."""
    n1 = KnowledgeNode(
        node_id="n1",
        topic_title="BFS",
        concept_summary="BFS basics",
        complexities=ComplexityAnalysis(time_complexity="O(V + E)", explanation="Adjacency list representation"),
        evidence_references=[EvidenceReference(evidence_id="e1", video_id="v1", start_seconds=0, end_seconds=10, video_position=1)]
    )

    n2 = KnowledgeNode(
        node_id="n2",
        topic_title="BFS",
        concept_summary="BFS matrix",
        complexities=ComplexityAnalysis(time_complexity="O(V^2)", explanation="Adjacency matrix representation"),
        evidence_references=[EvidenceReference(evidence_id="e2", video_id="v2", start_seconds=0, end_seconds=10, video_position=2)]
    )

    video_ikrs = [
        (1, IntermediateKnowledgeRepresentation(project_id="p1", title="V1", intent_category=IntentCategory.STUDY_NOTES, topic_nodes=[n1])),
        (2, IntermediateKnowledgeRepresentation(project_id="p2", title="V2", intent_category=IntentCategory.STUDY_NOTES, topic_nodes=[n2]))
    ]

    graph = cross_video_synthesis_engine.synthesize_playlist_knowledge(
        project_id="proj_pl4",
        playlist_id="pl_999",
        playlist_title="BFS Complexity Variants",
        video_ikrs=video_ikrs
    )

    assert len(graph.canonical_nodes) == 1
    assert len(graph.variants) == 1
    variant = graph.variants[0]
    assert variant.complexity.time_complexity == "O(V^2)"
    assert variant.video_position == 2
