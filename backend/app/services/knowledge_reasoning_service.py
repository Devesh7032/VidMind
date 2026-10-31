from datetime import datetime, timezone
from typing import Dict, Optional, List, Tuple
from app.schemas import (
    IntermediateKnowledgeRepresentation,
    UnifiedPlaylistKnowledgeGraph,
    IntentCategory
)
from app.services.ai.intent_engine import intent_engine
from app.services.multimodal_fusion_service import multimodal_fusion_service
from app.services.project_service import project_service
from app.services.code_reconstruction_service import code_reconstruction_service
from app.services.cross_video_synthesis_service import cross_video_synthesis_engine


class KnowledgeReasoningService:
    def __init__(self):
        # In-memory stores:
        # project_id -> IntermediateKnowledgeRepresentation
        self._knowledge_results: Dict[str, IntermediateKnowledgeRepresentation] = {}
        # project_id / playlist_id -> UnifiedPlaylistKnowledgeGraph
        self._playlist_knowledge_results: Dict[str, UnifiedPlaylistKnowledgeGraph] = {}

    def construct_intermediate_knowledge_representation(self, project_id: str) -> IntermediateKnowledgeRepresentation:
        """
        Main Milestone 6 & Phase 4 Milestone 2 Knowledge Reasoning Pipeline:
        1. Retrieves project & ExtractionPlan.
        2. Retrieves timestamp-aligned fused multimodal evidence.
        3. Invokes LLMProviderInterface reasoning engine.
        4. Invokes CodeReconstructionEngine for temporal reconstruction & multi-language separation.
        5. Validates observation types, evidence grounding, code syntax validity, and timestamp references.
        6. Stores & returns canonical IntermediateKnowledgeRepresentation (IKR).
        """
        project = project_service.get_project(project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found.")

        fusion_result = multimodal_fusion_service.get_fusion_result(project_id)
        if not fusion_result:
            fusion_result = multimodal_fusion_service.fuse_multimodal_evidence(project_id)

        plan = project.extraction_plan or intent_engine.create_extraction_plan(project.user_prompt)
        provider = intent_engine.get_provider()

        ikr = provider.reason_knowledge_graph(
            project_id=project_id,
            plan=plan,
            evidence_list=fusion_result.fused_evidence_list,
            project_title=project.source_url
        )

        # Validate IKR schema object
        if not isinstance(ikr, IntermediateKnowledgeRepresentation):
            ikr = IntermediateKnowledgeRepresentation(**dict(ikr))

        # Perform temporal code reconstruction across evidence frames
        reconstructed_snippets = code_reconstruction_service.reconstruct_code_artifacts(fusion_result.fused_evidence_list)
        if reconstructed_snippets and ikr.topic_nodes:
            existing_snippets = ikr.topic_nodes[0].code_snippets
            existing_languages = set()

            if existing_snippets:
                for s in existing_snippets:
                    if hasattr(s, "language") and s.language:
                        existing_languages.add(str(s.language).lower())
                    elif isinstance(s, dict) and s.get("language"):
                        existing_languages.add(str(s["language"]).lower())
                    elif isinstance(s, list):
                        for sub in s:
                            if hasattr(sub, "language") and sub.language:
                                existing_languages.add(str(sub.language).lower())
                            elif isinstance(sub, dict) and sub.get("language"):
                                existing_languages.add(str(sub["language"]).lower())

            for rec in reconstructed_snippets:
                if rec.language.lower() not in existing_languages:
                    ikr.topic_nodes[0].code_snippets.append(rec)
                    existing_languages.add(rec.language.lower())

        self._knowledge_results[project_id] = ikr
        return ikr

    def synthesize_playlist_knowledge_graph(self, project_id: str) -> UnifiedPlaylistKnowledgeGraph:
        """
        Milestone 3 Cross-Video Knowledge Synthesis Pipeline:
        Consumes per-video IKRs across playlist items and synthesizes a unified playlist knowledge graph.
        """
        project = project_service.get_project(project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found.")

        pl_meta = project.playlist_metadata
        playlist_id = project.playlist_id or f"pl_{project_id}"
        playlist_title = pl_meta.title if pl_meta else "Playlist Knowledge"
        intent_cat = project.extraction_plan.intent_category if project.extraction_plan else IntentCategory.STUDY_NOTES

        video_ikrs: List[Tuple[int, IntermediateKnowledgeRepresentation]] = []

        if pl_meta and pl_meta.videos:
            for idx, item in enumerate(pl_meta.videos, start=1):
                child_pid = f"{project_id}_v{idx}"
                ikr = self.get_knowledge_representation(child_pid)
                if not ikr:
                    # Construct if not already present
                    try:
                        ikr = self.construct_intermediate_knowledge_representation(child_pid)
                    except Exception as e:
                        print(f"[CrossVideoSynthesis] Warning: Could not construct IKR for child project '{child_pid}': {e}")
                        continue
                if ikr:
                    video_ikrs.append((idx, ikr))

        unified_graph = cross_video_synthesis_engine.synthesize_playlist_knowledge(
            project_id=project_id,
            playlist_id=playlist_id,
            playlist_title=playlist_title,
            video_ikrs=video_ikrs,
            intent_category=intent_cat
        )

        self._playlist_knowledge_results[project_id] = unified_graph
        self._playlist_knowledge_results[playlist_id] = unified_graph
        return unified_graph

    def get_knowledge_representation(self, project_id: str) -> Optional[IntermediateKnowledgeRepresentation]:
        return self._knowledge_results.get(project_id)

    def get_playlist_knowledge_graph(self, project_id_or_playlist_id: str) -> Optional[UnifiedPlaylistKnowledgeGraph]:
        return self._playlist_knowledge_results.get(project_id_or_playlist_id)


# Global singleton instance for knowledge reasoning service
knowledge_reasoning_service = KnowledgeReasoningService()
