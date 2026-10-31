import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from app.schemas import ProjectStatus
from app.services.project_service import project_service
from app.services.cache_service import cache_service, CacheType, CacheStatus


class StageName:
    INGEST = "INGEST"
    METADATA = "METADATA"
    TRANSCRIPT = "TRANSCRIPT"
    FRAMES = "FRAMES"
    VISION = "VISION"
    KNOWLEDGE_REASONING = "KNOWLEDGE_REASONING"
    ARTIFACT_GENERATION = "ARTIFACT_GENERATION"


class CheckpointStatus:
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CACHED = "CACHED"
    SKIPPED = "SKIPPED"


class CheckpointService:
    """
    VidMind Stage & Video-Level Checkpoint & Resumability Service.
    Tracks pipeline stage execution, saves recoverable state checkpoints,
    recovers interrupted single-video/playlist jobs, and avoids repeating completed stages.
    """

    def __init__(self):
        # In-memory checkpoint store: job_id -> video_id -> stage_name -> Checkpoint record
        self._checkpoints: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {}

    def save_stage_checkpoint(
        self,
        job_id: str,
        video_id: str,
        stage: str,
        status: str,
        checkpoint_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        if job_id not in self._checkpoints:
            self._checkpoints[job_id] = {}
        if video_id not in self._checkpoints[job_id]:
            self._checkpoints[job_id][video_id] = {}

        record = {
            "checkpoint_id": f"chk_{uuid.uuid4().hex[:8]}",
            "job_id": job_id,
            "video_id": video_id,
            "stage": stage,
            "status": status,
            "checkpoint_data": checkpoint_data or {},
            "error_message": error_message,
            "updated_at": now
        }

        self._checkpoints[job_id][video_id][stage] = record
        return record

    def get_stage_checkpoint(self, job_id: str, video_id: str, stage: str) -> Optional[Dict[str, Any]]:
        return self._checkpoints.get(job_id, {}).get(video_id, {}).get(stage)

    def is_stage_completed_or_cached(self, job_id: str, video_id: str, stage: str) -> bool:
        chk = self.get_stage_checkpoint(job_id, video_id, stage)
        if not chk:
            return False
        return chk["status"] in [CheckpointStatus.COMPLETED, CheckpointStatus.CACHED]

    def get_completed_stages(self, job_id: str, video_id: str = "main") -> List[str]:
        vid_chks = self._checkpoints.get(job_id, {}).get(video_id, {})
        return [
            stg for stg, rec in vid_chks.items()
            if rec["status"] in [CheckpointStatus.COMPLETED, CheckpointStatus.CACHED]
        ]

    def recover_stale_jobs(self, job_service_ref: Any) -> int:
        """Startup Recovery Policy: Scans and recovers unhandled RUNNING/PROCESSING jobs after application restart."""
        recovered_count = 0
        for j_id, job in job_service_ref._jobs.items():
            st = job.get("status")
            if st in [ProjectStatus.PROCESSING_VIDEO, ProjectStatus.VALIDATING_SOURCE, ProjectStatus.INGESTING_SOURCE]:
                job_service_ref.update_job_status(
                    job_id=j_id,
                    status=ProjectStatus.PROCESSING_VIDEO,
                    progress_percent=job.get("progress_percent", 50),
                    current_stage="Job recovered after server restart. Ready to resume.",
                    error_message=None
                )
                recovered_count += 1
        return recovered_count


# Global singleton instance for checkpoint service
checkpoint_service = CheckpointService()
