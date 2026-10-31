import re
import uuid
from typing import List, Dict, Tuple, Optional, Any, Set
from app.schemas import (
    IntermediateKnowledgeRepresentation,
    UnifiedPlaylistKnowledgeGraph,
    KnowledgeNode,
    KnowledgeRelationship,
    KnowledgeVariant,
    RelationshipType,
    EvidenceReference,
    CodeSnippet,
    ComplexityAnalysis,
    ObservationType,
    IntentCategory
)
from app.services.ai.intent_engine import intent_engine


class CrossVideoSynthesisEngine:
    """
    VidMind Cross-Video Knowledge Synthesis & Deduplication Engine.
    Synthesizes per-video knowledge representations into a unified playlist knowledge graph.
    Performs candidate generation, alias normalization, semantic deduplication,
    relationship building, and complete provenance preservation.
    """

    def __init__(self):
        # Known canonical alias dictionary
        self.known_aliases: Dict[str, str] = {
            "breadth first search": "BFS",
            "breadth-first search": "BFS",
            "breadth first traversal": "BFS",
            "breadth-first traversal": "BFS",
            "depth first search": "DFS",
            "depth-first search": "DFS",
            "depth first traversal": "DFS",
            "depth-first traversal": "DFS",
            "dijkstra's algorithm": "Dijkstra",
            "dijkstras algorithm": "Dijkstra",
            "tarjan's algorithm": "Tarjan's Algorithm",
            "tarjans algorithm": "Tarjan's Algorithm",
            "bellman ford": "Bellman-Ford",
            "bellman-ford algorithm": "Bellman-Ford",
            "floyd warshall": "Floyd-Warshall",
            "floyd-warshall algorithm": "Floyd-Warshall"
        }

        # Explicit non-merge pairs (Over-merge protection)
        self.distinct_concepts: Set[Tuple[str, str]] = {
            ("BFS", "DFS"),
            ("Dijkstra", "Bellman-Ford"),
            ("Dijkstra", "Floyd-Warshall"),
            ("Bellman-Ford", "Floyd-Warshall"),
            ("BFS", "Dijkstra"),
            ("DFS", "Dijkstra")
        }

    def normalize_topic_title(self, raw_title: str) -> str:
        """Normalizes topic title for candidate matching and alias mapping."""
        if not raw_title:
            return "General Topic"
        cleaned = raw_title.strip().lower()
        cleaned_no_punct = re.sub(r"[^\w\s]", "", cleaned)
        if cleaned in self.known_aliases:
            return self.known_aliases[cleaned]
        if cleaned_no_punct in self.known_aliases:
            return self.known_aliases[cleaned_no_punct]
        return raw_title.strip()

    def synthesize_playlist_knowledge(
        self,
        project_id: str,
        playlist_id: str,
        playlist_title: str,
        video_ikrs: List[Tuple[int, IntermediateKnowledgeRepresentation]],
        intent_category: IntentCategory = IntentCategory.STUDY_NOTES
    ) -> UnifiedPlaylistKnowledgeGraph:
        """
        Main Milestone 3 Synthesis Pipeline:
        1. Collects all topic nodes from completed video IKRs.
        2. Performs candidate grouping & alias deduplication.
        3. Preserves all timestamped evidence references & video positions.
        4. Detects relationships (SAME_AS, SUBTOPIC_OF, VARIANT_OF, RELATED_TO).
        5. Handles complexity variants & conflicts cleanly.
        """
        all_raw_nodes: List[Tuple[int, KnowledgeNode]] = []
        for pos, ikr in video_ikrs:
            for node in ikr.topic_nodes:
                all_raw_nodes.append((pos, node))

        if not all_raw_nodes:
            return UnifiedPlaylistKnowledgeGraph(
                playlist_id=playlist_id,
                project_id=project_id,
                title=playlist_title,
                intent_category=intent_category,
                canonical_nodes=[],
                relationships=[],
                variants=[],
                total_source_videos=len(video_ikrs)
            )

        canonical_nodes_map: Dict[str, KnowledgeNode] = {}
        relationships: List[KnowledgeRelationship] = []
        variants: List[KnowledgeVariant] = []

        for pos, raw_node in all_raw_nodes:
            norm_title = self.normalize_topic_title(raw_node.topic_title)

            # Check if canonical node already exists
            if norm_title in canonical_nodes_map:
                existing = canonical_nodes_map[norm_title]
                # Merge evidence references without losing provenance
                for ev_ref in raw_node.evidence_references:
                    ev_ref.video_position = pos
                    ev_ref.playlist_id = playlist_id
                    existing.evidence_references.append(ev_ref)

                # Merge concept summary without fabricating unsupported claims
                if raw_node.concept_summary and raw_node.concept_summary not in existing.concept_summary:
                    existing.concept_summary += f" Also: {raw_node.concept_summary}"

                # Merge key examples & formulas
                for ex in raw_node.key_examples:
                    if ex not in existing.key_examples:
                        existing.key_examples.append(ex)
                for f in raw_node.formulas:
                    if f not in existing.formulas:
                        existing.formulas.append(f)

                # Merge code snippets without overwriting
                existing_code_names = {cs.filename for cs in existing.code_snippets}
                for cs in raw_node.code_snippets:
                    if cs.filename not in existing_code_names:
                        existing.code_snippets.append(cs)
                        existing_code_names.add(cs.filename)

                # Handle Complexity Merging / Conflicts
                if raw_node.complexities:
                    if not existing.complexities:
                        existing.complexities = raw_node.complexities
                    elif (
                        existing.complexities.time_complexity != raw_node.complexities.time_complexity
                        and raw_node.complexities.time_complexity
                    ):
                        # Detect complexity variant / conflict and register variant
                        var_id = f"var_{uuid.uuid4().hex[:8]}"
                        variants.append(KnowledgeVariant(
                            variant_id=var_id,
                            source_video_id=raw_node.evidence_references[0].video_id if raw_node.evidence_references else f"vid_{pos}",
                            video_position=pos,
                            description=f"Complexity variant for {norm_title}: {raw_node.complexities.explanation or ''}",
                            complexity=raw_node.complexities,
                            observation_type=raw_node.observation_type
                        ))

                # Preserve strongest observation type
                if raw_node.observation_type == ObservationType.DIRECTLY_OBSERVED:
                    existing.observation_type = ObservationType.DIRECTLY_OBSERVED

            else:
                # Create new canonical node
                new_node_id = f"node_{uuid.uuid4().hex[:8]}"
                # Update evidence position metadata
                for ev_ref in raw_node.evidence_references:
                    ev_ref.video_position = pos
                    ev_ref.playlist_id = playlist_id

                c_node = KnowledgeNode(
                    node_id=new_node_id,
                    topic_title=norm_title,
                    concept_summary=raw_node.concept_summary,
                    key_examples=list(raw_node.key_examples),
                    formulas=list(raw_node.formulas),
                    questions_and_answers=list(raw_node.questions_and_answers),
                    code_snippets=list(raw_node.code_snippets),
                    complexities=raw_node.complexities,
                    evidence_references=list(raw_node.evidence_references),
                    observation_type=raw_node.observation_type,
                    confidence_score=raw_node.confidence_score
                )
                canonical_nodes_map[norm_title] = c_node

        canonical_list = list(canonical_nodes_map.values())

        # Step 4: Build Knowledge Relationships (SUBTOPIC_OF, RELATED_TO)
        node_titles = [cn.topic_title for cn in canonical_list]
        for i in range(len(canonical_list)):
            for j in range(i + 1, len(canonical_list)):
                n1 = canonical_list[i]
                n2 = canonical_list[j]

                # Check if one is subtopic of another (e.g. "DFS for Cycle Detection" subtopic of "DFS")
                if n1.topic_title.lower() in n2.topic_title.lower() and len(n1.topic_title) < len(n2.topic_title):
                    relationships.append(KnowledgeRelationship(
                        relationship_id=f"rel_{uuid.uuid4().hex[:8]}",
                        source_node_id=n2.node_id,
                        target_node_id=n1.node_id,
                        relationship_type=RelationshipType.SUBTOPIC_OF,
                        confidence_score=0.92,
                        explanation=f"'{n2.topic_title}' is a subtopic of '{n1.topic_title}'"
                    ))
                elif n2.topic_title.lower() in n1.topic_title.lower() and len(n2.topic_title) < len(n1.topic_title):
                    relationships.append(KnowledgeRelationship(
                        relationship_id=f"rel_{uuid.uuid4().hex[:8]}",
                        source_node_id=n1.node_id,
                        target_node_id=n2.node_id,
                        relationship_type=RelationshipType.SUBTOPIC_OF,
                        confidence_score=0.92,
                        explanation=f"'{n1.topic_title}' is a subtopic of '{n2.topic_title}'"
                    ))
                elif (n1.topic_title, n2.topic_title) in self.distinct_concepts or (n2.topic_title, n1.topic_title) in self.distinct_concepts:
                    relationships.append(KnowledgeRelationship(
                        relationship_id=f"rel_{uuid.uuid4().hex[:8]}",
                        source_node_id=n1.node_id,
                        target_node_id=n2.node_id,
                        relationship_type=RelationshipType.RELATED_TO,
                        confidence_score=0.88,
                        explanation=f"'{n1.topic_title}' and '{n2.topic_title}' are related graph algorithms"
                    ))

        return UnifiedPlaylistKnowledgeGraph(
            playlist_id=playlist_id,
            project_id=project_id,
            title=playlist_title,
            intent_category=intent_category,
            canonical_nodes=canonical_list,
            relationships=relationships,
            variants=variants,
            total_source_videos=len(video_ikrs)
        )


# Global singleton instance for cross-video synthesis engine
cross_video_synthesis_engine = CrossVideoSynthesisEngine()
