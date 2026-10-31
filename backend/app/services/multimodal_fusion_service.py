import os
import uuid
import tempfile
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from app.schemas import (
    ExtractionPlan,
    TranscriptSegment,
    VisualObservation,
    FusedEvidence,
    ObservationType,
    MultimodalFusionResponse,
    ContentType,
    VisualContentType
)
from app.services.ai.intent_engine import intent_engine
from app.services.ingestion_service import ingestion_service
from app.services.project_service import project_service
from app.services.video_frame_extractor import video_frame_extractor

# Resource Limits
MAX_ANALYZED_FRAMES_PER_VIDEO = 10
WINDOW_PADDING_SECONDS = 5.0

CODE_KEYWORDS = [
    "code", "function", "def ", "class ", "algorithm", "implement", "python", "var", "return",
    "void ", "int ", "solution", "array", "vector", "write", "loop", "string", "include",
    "import", "print", "stdout", "main", "struct", "node", "pointer", "index", "equal",
    "output", "compiler", "syntax", "ide", "java", "c++", "cpp", "js", "javascript",
    "rust", "golang", "sql", "html", "css", "program", "method", "variable", "for ", "while "
]


class MultimodalFusionService:
    def __init__(self):
        # In-memory store: project_id -> MultimodalFusionResponse
        self._fusion_results: Dict[str, MultimodalFusionResponse] = {}

    def select_relevant_transcript_segments(
        self,
        segments: List[TranscriptSegment],
        plan: ExtractionPlan
    ) -> List[TranscriptSegment]:
        """
        Transcript-guided selection: Identifies transcript segments matching requested content types.
        """
        if not segments:
            return []

        keywords = set()
        for ct in plan.content_types:
            if ct == ContentType.CODE:
                keywords.update(CODE_KEYWORDS)
            elif ct == ContentType.FORMULAS:
                keywords.update(["formula", "equation", "math", "derive", "equal", "constant", "proof"])
            elif ct == ContentType.TIME_COMPLEXITY or ct == ContentType.SPACE_COMPLEXITY:
                keywords.update(["complexity", "time", "space", "o(", "big o", "n log n", "theta"])
            elif ct == ContentType.QUESTIONS_ANSWERS:
                keywords.update(["question", "answer", "interview", "why", "how", "explain"])
            elif ct == ContentType.CONCEPTS or ct == ContentType.DEFINITIONS:
                keywords.update(["concept", "definition", "overview", "intro", "learn", "summary", "key"])

        relevant = []
        for seg in segments:
            text_lower = seg.text.lower()
            if any(kw in text_lower for kw in keywords):
                relevant.append(seg)

        if not relevant:
            step = max(1, len(segments) // 5)
            relevant = segments[::step]

        return relevant

    def generate_timestamp_windows(
        self,
        relevant_segments: List[TranscriptSegment],
        max_duration_seconds: int
    ) -> List[Tuple[float, float]]:
        """
        Generates candidate timestamp windows (start_seconds, end_seconds) with padding.
        Falls back to broad sampling across video duration if segment evidence is sparse (< 3 windows).
        """
        dur = max(30, max_duration_seconds)
        
        if not relevant_segments:
            step = dur / 7.0
            return [(round(step * i, 1), round(step * i + 20, 1)) for i in range(1, 7)]

        windows = []
        for seg in relevant_segments:
            start = max(0.0, round(seg.start_seconds - WINDOW_PADDING_SECONDS, 1))
            end = min(float(dur), round(seg.end_seconds + WINDOW_PADDING_SECONDS, 1))
            windows.append((start, end))

        windows.sort(key=lambda w: w[0])
        merged = []
        for w in windows:
            if not merged:
                merged.append(w)
            else:
                last_start, last_end = merged[-1]
                if w[0] <= last_end:
                    merged[-1] = (last_start, max(last_end, w[1]))
                else:
                    merged.append(w)

        # Requirement 12: If transcript evidence is sparse (< 3 candidate windows), fall back to broader visual sampling across video
        if len(merged) < 3:
            step = dur / 6.0
            broad_windows = [(round(step * i, 1), round(step * i + 15, 1)) for i in range(1, 6)]
            for bw in broad_windows:
                if not any(abs(bw[0] - m[0]) < 10 for m in merged):
                    merged.append(bw)
            merged.sort(key=lambda w: w[0])

        return merged

    def fuse_multimodal_evidence(self, project_id: str) -> MultimodalFusionResponse:
        """
        Main Multimodal Fusion Pipeline:
        1. Ingests transcript and video source.
        2. Downloads low-resolution video stream via yt-dlp.
        3. Extracts real video keyframe images at candidate timestamps via OpenCV.
        4. Applies perceptual duplicate frame filtering.
        5. Performs Gemini Vision analysis on real frame images.
        6. Combines transcript + visual observations into timestamp-aligned FusedEvidence.
        """
        project = project_service.get_project(project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found.")

        ingestion = ingestion_service.get_ingestion_result(project_id)
        if not ingestion:
            ingestion = ingestion_service.process_ingestion(project_id, project.source_url)

        plan = project.extraction_plan or intent_engine.create_extraction_plan(project.user_prompt)

        # 1. Transcript-Guided Selection & Timestamp Windowing
        relevant_segments = self.select_relevant_transcript_segments(ingestion.transcript_segments, plan)
        video_duration = ingestion.video_metadata.duration_seconds
        windows = self.generate_timestamp_windows(relevant_segments, video_duration)
        candidate_timestamps = [round((w[0] + w[1]) / 2.0, 1) for w in windows]

        # 2. Real Video Stream Download & Keyframe Extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            video_filepath = video_frame_extractor.download_low_res_stream(project.source_url, temp_dir)
            extracted_frames = []
            if video_filepath and os.path.exists(video_filepath):
                extracted_frames = video_frame_extractor.extract_keyframes_from_file(
                    video_filepath=video_filepath,
                    candidate_timestamps=candidate_timestamps,
                    max_frames=MAX_ANALYZED_FRAMES_PER_VIDEO
                )

        # Diagnostic logging (Safe metadata only, NO secrets)
        print(f"[MultimodalFusion Diagnostics - Project {project_id}]")
        print(f"  Transcript Status: {ingestion.transcript_status.value}")
        print(f"  Total Transcript Segments: {len(ingestion.transcript_segments)}")
        print(f"  Selected Transcript Segments: {len(relevant_segments)}")
        print(f"  Candidate Windows Count: {len(windows)}")
        print(f"  Extracted Keyframes Count: {len(extracted_frames)}")

        provider = intent_engine.get_provider()
        fused_list: List[FusedEvidence] = []

        # 3. Vision Analysis & Multimodal Evidence Fusion
        if extracted_frames:
            for frame_rec in extracted_frames:
                frame_t = frame_rec["timestamp_seconds"]
                img_bytes = frame_rec["image_bytes"]
                ev_id = f"ev_{uuid.uuid4().hex[:8]}"

                # Match transcript text if available near this timestamp
                matching_seg_text = "[Audio transcript unavailable - Visual frame evidence extracted]"
                for seg in ingestion.transcript_segments:
                    if seg.start_seconds <= frame_t <= seg.end_seconds + 5.0:
                        matching_seg_text = seg.text
                        break

                try:
                    time.sleep(0.3)
                    vis_obs = provider.analyze_visual_frame(
                        frame_timestamp=frame_t,
                        image_bytes=img_bytes,
                        context_hint=f"{project.user_prompt} {matching_seg_text[:100]}"
                    )
                except Exception as e:
                    print(f"[MultimodalFusion] Vision analysis failed at {frame_t:.1f}s: {e}")
                    vis_obs = None

                fused_list.append(FusedEvidence(
                    evidence_id=ev_id,
                    video_id=ingestion.video_metadata.video_id,
                    start_seconds=max(0.0, frame_t - 5.0),
                    end_seconds=frame_t + 5.0,
                    transcript_text=matching_seg_text,
                    visual_observation=vis_obs,
                    observation_type=ObservationType.DIRECTLY_OBSERVED if vis_obs else ObservationType.RECONSTRUCTED,
                    confidence_score=0.94 if vis_obs else 0.70
                ))
        elif relevant_segments:
            # Fallback if video stream download failed but transcript is available
            for seg in relevant_segments[:MAX_ANALYZED_FRAMES_PER_VIDEO]:
                ev_id = f"ev_{uuid.uuid4().hex[:8]}"
                fused_list.append(FusedEvidence(
                    evidence_id=ev_id,
                    video_id=ingestion.video_metadata.video_id,
                    start_seconds=seg.start_seconds,
                    end_seconds=seg.end_seconds,
                    transcript_text=seg.text,
                    visual_observation=None,
                    observation_type=ObservationType.DIRECTLY_OBSERVED,
                    confidence_score=0.85
                ))

        # Check for Insufficient Evidence state
        if not fused_list:
            raise RuntimeError(
                "I couldn't extract enough reliable information from this video to create the requested knowledge pack. "
                "The transcript was unavailable and video frame extraction yielded no extractable evidence."
            )

        response = MultimodalFusionResponse(
            project_id=project_id,
            total_evidence_count=len(fused_list),
            fused_evidence_list=fused_list,
            fusion_completed_at=datetime.now(timezone.utc)
        )

        self._fusion_results[project_id] = response
        return response

    def get_fusion_result(self, project_id: str) -> Optional[MultimodalFusionResponse]:
        return self._fusion_results.get(project_id)


# Global singleton instance for multimodal fusion service
multimodal_fusion_service = MultimodalFusionService()
