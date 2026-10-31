import asyncio
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Optional, AsyncGenerator, List, Any
from app.config import settings
from app.schemas import (
    JobStatusResponse,
    ProjectStatus,
    SSEProgressEvent,
    PlaylistJobStatus,
    VideoJobStatus,
    PlaylistVideoItem,
    ErrorCategory,
    ErrorDetail
)
from app.services.project_service import project_service
from app.services.ingestion_service import ingestion_service
from app.services.multimodal_fusion_service import multimodal_fusion_service
from app.services.knowledge_reasoning_service import knowledge_reasoning_service
from app.services.artifact_service import artifact_service
from app.services.cache_service import cache_service, CacheType, CacheStatus
from app.services.checkpoint_service import checkpoint_service, StageName, CheckpointStatus

STAGE_WATCHDOG_TIMEOUT_SECONDS = 180.0


def classify_error(e: Exception, stage: str = "UNKNOWN") -> ErrorDetail:
    err_str = str(e).lower()
    tech_details = f"{type(e).__name__}: {str(e)}"

    if isinstance(e, UnicodeEncodeError) or "charmap" in err_str or "codec" in err_str or "encoding" in err_str:
        return ErrorDetail(
            code=ErrorCategory.ENCODING_ERROR,
            message="I couldn't complete the extraction because the processing service encountered a text encoding problem while preparing the extracted content.",
            stage=stage,
            retryable=True,
            technical_details="Unicode encoding error."
        )
    elif "quota" in err_str or "rate limit" in err_str or "429" in err_str:
        return ErrorDetail(
            code=ErrorCategory.QUOTA_EXCEEDED,
            message="I couldn't continue the extraction because the AI processing quota is temporarily unavailable. Your completed processing steps have been preserved.",
            stage=stage,
            retryable=True,
            technical_details="AI processing quota limit reached."
        )
    elif "timeout" in err_str or isinstance(e, TimeoutError):
        return ErrorDetail(
            code=ErrorCategory.TIMEOUT,
            message="The extraction stage timed out before completing.",
            stage=stage,
            retryable=True,
            technical_details=tech_details
        )
    elif "unavailable" in err_str and "video" in err_str:
        return ErrorDetail(
            code=ErrorCategory.VIDEO_UNAVAILABLE,
            message="The video content could not be retrieved or is unavailable.",
            stage=stage,
            retryable=False,
            technical_details=tech_details
        )
    elif "transcript" in err_str:
        return ErrorDetail(
            code=ErrorCategory.TRANSCRIPT_UNAVAILABLE,
            message="Captions/transcript could not be retrieved for this video.",
            stage=stage,
            retryable=True,
            technical_details=tech_details
        )
    else:
        return ErrorDetail(
            code=ErrorCategory.UNKNOWN_ERROR,
            message=f"I couldn't complete the extraction due to a processing error during {stage}.",
            stage=stage,
            retryable=True,
            technical_details=tech_details
        )


class JobService:
    """
    VidMind Job Service with Job Watchdog, Stage-Level Timeouts, Cache Reuse,
    Stage Checkpoints, Failure Recovery, Structured Error Categories, and SSE Progress Streaming.
    """

    def __init__(self):
        # In-memory job repository
        self._jobs: Dict[str, Dict] = {}
        # SSE Event Listeners: job_id -> List[asyncio.Queue]
        self._subscribers: Dict[str, list] = {}

    def get_active_job_for_project(self, project_id: str) -> Optional[JobStatusResponse]:
        """Duplicate-Job Protection: Finds any active or pending job for the project."""
        for j in self._jobs.values():
            if j["project_id"] == project_id and j["status"] in [
                ProjectStatus.PENDING,
                ProjectStatus.PROCESSING_VIDEO,
                ProjectStatus.VALIDATING_SOURCE,
                ProjectStatus.INGESTING_SOURCE,
                ProjectStatus.FUSING_MULTIMODAL_EVIDENCE,
                ProjectStatus.REASONING_KNOWLEDGE
            ]:
                return JobStatusResponse(**j)
        return None

    def create_job(self, project_id: str) -> JobStatusResponse:
        active = self.get_active_job_for_project(project_id)
        if active:
            return active

        project = project_service.get_project(project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found.")

        job_id = f"job_{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc)

        is_playlist = bool(project.is_playlist)
        total_videos = 1
        video_items = []

        if is_playlist and project.playlist_metadata:
            total_videos = project.playlist_metadata.total_videos
            video_items = project.playlist_metadata.videos

        job_record = {
            "job_id": job_id,
            "project_id": project_id,
            "status": ProjectStatus.PENDING,
            "progress_percent": 0,
            "current_stage": "Job queued. Preparing content source..." if not is_playlist else "Playlist queued. Discovering videos...",
            "error_message": None,
            "error_details": None,
            "is_playlist": is_playlist,
            "total_videos": total_videos,
            "completed_videos": 0,
            "failed_videos": 0,
            "current_video_title": None,
            "video_items": [v.model_dump() if hasattr(v, "model_dump") else v for v in video_items],
            "created_at": now,
            "updated_at": now,
            "details": {}
        }

        self._jobs[job_id] = job_record
        self._subscribers[job_id] = []
        return JobStatusResponse(**job_record)

    def get_job(self, job_id: str) -> Optional[JobStatusResponse]:
        record = self._jobs.get(job_id)
        if not record:
            return None
        return JobStatusResponse(**record)

    def resume_job(self, job_id: str) -> JobStatusResponse:
        """Resumes an interrupted or failed job from its last valid stage checkpoint."""
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job '{job_id}' not found.")

        res = self.update_job_status(
            job_id=job_id,
            status=ProjectStatus.PROCESSING_VIDEO,
            progress_percent=max(job.progress_percent, 10),
            current_stage="Resuming job from last valid stage checkpoint...",
            error_message=None,
            error_details=None
        )
        return res

    def update_job_status(
        self,
        job_id: str,
        status: ProjectStatus,
        progress_percent: int,
        current_stage: str,
        error_message: Optional[str] = None,
        error_details: Optional[ErrorDetail] = None,
        is_playlist: Optional[bool] = None,
        total_videos: Optional[int] = None,
        completed_videos: Optional[int] = None,
        failed_videos: Optional[int] = None,
        current_video_title: Optional[str] = None,
        details: Optional[Dict] = None
    ) -> Optional[JobStatusResponse]:
        record = self._jobs.get(job_id)
        if not record:
            return None

        record["status"] = status
        record["progress_percent"] = max(0, min(100, progress_percent))
        record["current_stage"] = current_stage
        record["updated_at"] = datetime.now(timezone.utc)
        if error_message is not None:
            record["error_message"] = error_message
        if error_details is not None:
            record["error_details"] = error_details.model_dump() if hasattr(error_details, "model_dump") else error_details
        if is_playlist is not None:
            record["is_playlist"] = is_playlist
        if total_videos is not None:
            record["total_videos"] = total_videos
        if completed_videos is not None:
            record["completed_videos"] = completed_videos
        if failed_videos is not None:
            record["failed_videos"] = failed_videos
        if current_video_title is not None:
            record["current_video_title"] = current_video_title
        if details:
            record["details"].update(details)

        project_service.update_status(record["project_id"], status, error_message)

        event = SSEProgressEvent(
            job_id=job_id,
            project_id=record["project_id"],
            status=status,
            progress_percent=record["progress_percent"],
            current_stage=current_stage,
            message=error_message or current_stage,
            error_details=record.get("error_details"),
            is_playlist=record.get("is_playlist", False),
            total_videos=record.get("total_videos", 1),
            completed_videos=record.get("completed_videos", 0),
            failed_videos=record.get("failed_videos", 0),
            current_video_title=record.get("current_video_title")
        )
        self._notify_subscribers(job_id, event)

        return JobStatusResponse(**record)

    def _notify_subscribers(self, job_id: str, event: SSEProgressEvent):
        queues = self._subscribers.get(job_id, [])
        event_json = event.model_dump_json()
        for q in queues:
            try:
                q.put_nowait(event_json)
            except Exception:
                pass

    async def subscribe_job_stream(self, job_id: str) -> AsyncGenerator[str, None]:
        job = self.get_job(job_id)
        if not job:
            yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
            return

        q = asyncio.Queue()
        if job_id not in self._subscribers:
            self._subscribers[job_id] = []
        self._subscribers[job_id].append(q)

        initial_event = SSEProgressEvent(
            job_id=job.job_id,
            project_id=job.project_id,
            status=job.status,
            progress_percent=job.progress_percent,
            current_stage=job.current_stage,
            message="Stream connected",
            error_details=job.error_details,
            is_playlist=job.is_playlist,
            total_videos=job.total_videos,
            completed_videos=job.completed_videos,
            failed_videos=job.failed_videos,
            current_video_title=job.current_video_title
        )
        yield f"data: {initial_event.model_dump_json()}\n\n"

        try:
            while True:
                data = await q.get()
                yield f"data: {data}\n\n"
                parsed = json.loads(data)
                term_states = [
                    ProjectStatus.COMPLETED.value,
                    ProjectStatus.PARTIALLY_FAILED.value,
                    ProjectStatus.FAILED.value
                ]
                if parsed.get("status") in term_states:
                    break
        except asyncio.CancelledError:
            pass
        finally:
            if job_id in self._subscribers and q in self._subscribers[job_id]:
                self._subscribers[job_id].remove(q)

    async def _process_single_video_pipeline(
        self,
        project_id: str,
        video_url: str,
        video_title: str,
        parent_project: Optional[Any] = None,
        job_id: str = "main_job",
        delay_step: float = 0.05
    ) -> Dict[str, Any]:
        """
        Executes single-video pipeline with Cache Hit/Miss logic and Stage Checkpointing.
        """
        proj = project_service.get_project(project_id)
        if not proj and parent_project:
            plan_dict = parent_project.extraction_plan.model_dump() if parent_project.extraction_plan else None
            project_record = {
                "project_id": project_id,
                "source_url": video_url,
                "user_prompt": parent_project.user_prompt,
                "status": ProjectStatus.PROCESSING_VIDEO,
                "is_playlist": False,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "extraction_plan": plan_dict,
                "artifact_summary": None,
                "error_message": None
            }
            project_service._projects[project_id] = project_record
            proj = project_service.get_project(project_id)

        intent_cat = proj.extraction_plan.intent_category if proj and proj.extraction_plan else "STUDY_NOTES"
        u_prompt = proj.user_prompt if proj else ""
        v_fingerprint = cache_service.generate_content_fingerprint(video_url)
        p_fingerprint = cache_service.generate_processing_fingerprint(str(intent_cat), u_prompt)

        # 1. Stage: INGESTION & METADATA
        if checkpoint_service.is_stage_completed_or_cached(job_id, video_url, StageName.INGEST):
            cached_ing = cache_service.get_cache(CacheType.TRANSCRIPT, video_url, v_fingerprint)
            if cached_ing:
                ing_res = cached_ing
            else:
                ing_res = ingestion_service.process_ingestion(project_id=project_id, source_url=video_url)
                cache_service.commit_cache(CacheType.TRANSCRIPT, video_url, v_fingerprint, ing_res)
        else:
            checkpoint_service.save_stage_checkpoint(job_id, video_url, StageName.INGEST, CheckpointStatus.RUNNING)
            ing_res = ingestion_service.process_ingestion(project_id=project_id, source_url=video_url)
            cache_service.commit_cache(CacheType.TRANSCRIPT, video_url, v_fingerprint, ing_res)
            checkpoint_service.save_stage_checkpoint(job_id, video_url, StageName.INGEST, CheckpointStatus.COMPLETED)

        # 2. Stage: MULTIMODAL FUSION
        if not checkpoint_service.is_stage_completed_or_cached(job_id, video_url, StageName.VISION):
            checkpoint_service.save_stage_checkpoint(job_id, video_url, StageName.VISION, CheckpointStatus.RUNNING)
            fusion_res = multimodal_fusion_service.fuse_multimodal_evidence(project_id=project_id)
            cache_service.commit_cache(CacheType.VISION, video_url, p_fingerprint, fusion_res)
            checkpoint_service.save_stage_checkpoint(job_id, video_url, StageName.VISION, CheckpointStatus.COMPLETED)

        # 3. Stage: KNOWLEDGE REASONING
        if checkpoint_service.is_stage_completed_or_cached(job_id, video_url, StageName.KNOWLEDGE_REASONING):
            cached_ikr = cache_service.get_cache(CacheType.KNOWLEDGE, video_url, p_fingerprint)
            if cached_ikr:
                ikr_res = cached_ikr
            else:
                ikr_res = knowledge_reasoning_service.construct_intermediate_knowledge_representation(project_id=project_id)
                cache_service.commit_cache(CacheType.KNOWLEDGE, video_url, p_fingerprint, ikr_res)
        else:
            checkpoint_service.save_stage_checkpoint(job_id, video_url, StageName.KNOWLEDGE_REASONING, CheckpointStatus.RUNNING)
            ikr_res = knowledge_reasoning_service.construct_intermediate_knowledge_representation(project_id=project_id)
            cache_service.commit_cache(CacheType.KNOWLEDGE, video_url, p_fingerprint, ikr_res)
            checkpoint_service.save_stage_checkpoint(job_id, video_url, StageName.KNOWLEDGE_REASONING, CheckpointStatus.COMPLETED)

        # 4. Stage: ARTIFACT GENERATION
        checkpoint_service.save_stage_checkpoint(job_id, video_url, StageName.ARTIFACT_GENERATION, CheckpointStatus.RUNNING)
        art_res = artifact_service.generate_project_artifacts(project_id=project_id)
        checkpoint_service.save_stage_checkpoint(job_id, video_url, StageName.ARTIFACT_GENERATION, CheckpointStatus.COMPLETED)

        return {
            "title": video_title,
            "url": video_url,
            "artifacts_count": art_res.total_artifacts,
            "generated_files": [a.filename for a in art_res.artifacts]
        }

    async def execute_background_job(self, job_id: str, trigger_failure: bool = False, delay_step: float = 0.05):
        """
        Executes background job with Job Watchdog, Timeout Protections, Cache reuse,
        Stage Checkpointing, and Structured Error Handling.
        """
        job = self.get_job(job_id)
        if not job:
            return

        project = project_service.get_project(job.project_id)
        if not project:
            err_detail = ErrorDetail(
                code=ErrorCategory.VALIDATION_ERROR,
                message=f"Project '{job.project_id}' not found.",
                stage="INIT",
                retryable=False
            )
            self.update_job_status(
                job_id=job_id,
                status=ProjectStatus.FAILED,
                progress_percent=0,
                current_stage="Associated project not found.",
                error_message=f"Project '{job.project_id}' not found.",
                error_details=err_detail
            )
            return

        try:
            # Wrap execution in Stage Watchdog Timeout (180s cap)
            async with asyncio.timeout(STAGE_WATCHDOG_TIMEOUT_SECONDS):
                if not project.is_playlist:
                    self.update_job_status(job_id=job_id, status=ProjectStatus.VALIDATING_SOURCE, progress_percent=15, current_stage="Checking your video source...")
                    await asyncio.sleep(delay_step)

                    if trigger_failure:
                        raise RuntimeError("Simulated processing error during single video pipeline.")

                    self.update_job_status(job_id=job_id, status=ProjectStatus.INGESTING_SOURCE, progress_percent=30, current_stage="Preparing video content & transcript...")
                    await asyncio.sleep(delay_step)

                    self.update_job_status(job_id=job_id, status=ProjectStatus.FUSING_MULTIMODAL_EVIDENCE, progress_percent=50, current_stage="Combining spoken and visual information...")
                    await asyncio.sleep(delay_step)

                    self.update_job_status(job_id=job_id, status=ProjectStatus.REASONING_KNOWLEDGE, progress_percent=70, current_stage="Understanding the important information...")
                    await asyncio.sleep(delay_step)

                    self.update_job_status(job_id=job_id, status=ProjectStatus.GENERATING_ARTIFACT, progress_percent=85, current_stage="Preparing your knowledge document & downloadable files...")
                    await asyncio.sleep(delay_step)

                    res = await self._process_single_video_pipeline(
                        project.project_id,
                        project.source_url,
                        "Single Video",
                        parent_project=project,
                        job_id=job_id,
                        delay_step=delay_step
                    )

                    self.update_job_status(
                        job_id=job_id,
                        status=ProjectStatus.COMPLETED,
                        progress_percent=100,
                        current_stage="Your knowledge pack is ready.",
                        completed_videos=1,
                        total_videos=1,
                        details=res
                    )
                else:
                    # --- PLAYLIST MULTI-VIDEO PIPELINE ---
                    pl_meta = project.playlist_metadata
                    if not pl_meta or not pl_meta.videos:
                        err_detail = ErrorDetail(
                            code=ErrorCategory.VALIDATION_ERROR,
                            message="Playlist contains no videos to process.",
                            stage="DISCOVERY",
                            retryable=False
                        )
                        self.update_job_status(
                            job_id=job_id,
                            status=ProjectStatus.FAILED,
                            progress_percent=0,
                            current_stage="Playlist contains no videos to process.",
                            error_details=err_detail
                        )
                        return

                    video_items = pl_meta.videos
                    total_vids = len(video_items)
                    completed_count = 0
                    failed_count = 0

                    self.update_job_status(
                        job_id=job_id,
                        status=ProjectStatus.PROCESSING_VIDEO,
                        progress_percent=5,
                        current_stage=f"Playlist discovered ({total_vids} videos). Checking cached videos & checkpoints...",
                        is_playlist=True,
                        total_videos=total_vids,
                        completed_videos=0,
                        failed_videos=0
                    )

                    max_concurrency = settings.max_concurrent_videos
                    sem = asyncio.Semaphore(max_concurrency)

                    async def process_child_video(idx: int, item: PlaylistVideoItem):
                        nonlocal completed_count, failed_count
                        
                        if item.status == VideoJobStatus.COMPLETED or item.status == VideoJobStatus.SKIPPED:
                            completed_count += 1
                            return

                        async with sem:
                            v_title = item.title or f"Video #{idx}"
                            self.update_job_status(
                                job_id=job_id,
                                status=ProjectStatus.PROCESSING_VIDEO,
                                progress_percent=int(5 + ((completed_count + failed_count) / total_vids) * 80),
                                current_stage=f"Processing video {idx} of {total_vids}: {v_title}",
                                current_video_title=v_title
                            )

                            try:
                                child_pid = f"{project.project_id}_v{idx}"
                                await self._process_single_video_pipeline(
                                    child_pid,
                                    item.source_url,
                                    v_title,
                                    parent_project=project,
                                    job_id=f"{job_id}_v{idx}",
                                    delay_step=delay_step
                                )
                                completed_count += 1
                                item.status = VideoJobStatus.COMPLETED
                            except Exception as ve:
                                print(f"[PlaylistWorker] Video {idx} ('{v_title}') failed: {ve}")
                                failed_count += 1
                                item.status = VideoJobStatus.FAILED
                                item.error_message = str(ve)

                            new_pct = int(5 + ((completed_count + failed_count) / total_vids) * 80)
                            self.update_job_status(
                                job_id=job_id,
                                status=ProjectStatus.PROCESSING_VIDEO,
                                progress_percent=new_pct,
                                current_stage=f"Completed {completed_count}/{total_vids} videos.",
                                completed_videos=completed_count,
                                failed_videos=failed_count,
                                current_video_title=v_title
                            )

                    tasks = [process_child_video(i, item) for i, item in enumerate(video_items, start=1)]
                    await asyncio.gather(*tasks, return_exceptions=True)

                    if completed_count > 0:
                        try:
                            self.update_job_status(
                                job_id=job_id,
                                status=ProjectStatus.CROSS_VIDEO_SYNTHESIS,
                                progress_percent=90,
                                current_stage="Combining knowledge from your videos...",
                                completed_videos=completed_count,
                                failed_videos=failed_count
                            )
                            await asyncio.sleep(delay_step)

                            self.update_job_status(
                                job_id=job_id,
                                status=ProjectStatus.DEDUPLICATION,
                                progress_percent=94,
                                current_stage="Finding duplicate topics & consolidating evidence...",
                                completed_videos=completed_count,
                                failed_videos=failed_count
                            )
                            await asyncio.sleep(delay_step)

                            self.update_job_status(
                                job_id=job_id,
                                status=ProjectStatus.RELATIONSHIP_BUILDING,
                                progress_percent=98,
                                current_stage="Connecting related concepts...",
                                completed_videos=completed_count,
                                failed_videos=failed_count
                            )
                            await asyncio.sleep(delay_step)

                            unified_graph = knowledge_reasoning_service.synthesize_playlist_knowledge_graph(project.project_id)
                        except Exception as se:
                            print(f"[CrossVideoSynthesis] Warning during playlist synthesis: {se}")

                    if completed_count == total_vids:
                        final_status = ProjectStatus.COMPLETED
                        final_msg = f"All {total_vids} playlist videos processed and synthesized successfully."
                    elif completed_count > 0:
                        final_status = ProjectStatus.PARTIALLY_FAILED
                        final_msg = f"Playlist processing completed partially ({completed_count} succeeded, {failed_count} failed)."
                    else:
                        final_status = ProjectStatus.FAILED
                        final_msg = f"Playlist processing failed. All {total_vids} videos failed."

                    self.update_job_status(
                        job_id=job_id,
                        status=final_status,
                        progress_percent=100 if final_status != ProjectStatus.FAILED else 0,
                        current_stage=final_msg,
                        error_message=final_msg if final_status != ProjectStatus.COMPLETED else None,
                        completed_videos=completed_count,
                        failed_videos=failed_count,
                        details={
                            "total_videos": total_vids,
                            "completed_videos": completed_count,
                            "failed_videos": failed_count,
                            "video_statuses": [item.model_dump() for item in video_items]
                        }
                    )
        except TimeoutError as te:
            err_detail = classify_error(te, stage="WATCHDOG_TIMEOUT")
            self.update_job_status(
                job_id=job_id,
                status=ProjectStatus.FAILED,
                progress_percent=0,
                current_stage=err_detail.message,
                error_message=err_detail.message,
                error_details=err_detail
            )
        except Exception as e:
            latest_job = self.get_job(job_id)
            curr_stage = latest_job.current_stage if latest_job else "PROCESSING"
            err_detail = classify_error(e, stage=curr_stage)
            
            # Print safe server log without raw exceptions
            print(f"[JOB EXCEPTION] Job ID: {job_id} | Stage: {curr_stage} | Code: {err_detail.code} | TechDetails: {err_detail.technical_details}")
            
            self.update_job_status(
                job_id=job_id,
                status=ProjectStatus.FAILED,
                progress_percent=0,
                current_stage=err_detail.message,
                error_message=err_detail.message,
                error_details=err_detail
            )


# Global singleton instance for job service
job_service = JobService()
