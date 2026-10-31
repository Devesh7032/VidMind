from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import StreamingResponse
from app.schemas import JobCreateResponse, JobStatusResponse
from app.services.job_service import job_service
from app.services.project_service import project_service
from app.services.cache_service import cache_service

router = APIRouter(prefix="/api", tags=["Jobs & Caching"])


@router.post(
    "/projects/{project_id}/analyze",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def analyze_project(
    project_id: str,
    background_tasks: BackgroundTasks,
    trigger_failure: bool = False
):
    """
    Trigger an asynchronous processing job for a registered project.
    Enqueues processing task in background and returns job_id immediately.
    """
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found."
        )

    try:
        job = job_service.create_job(project_id)
        # Dispatch background worker task
        background_tasks.add_task(
            job_service.execute_background_job,
            job_id=job.job_id,
            trigger_failure=trigger_failure
        )
        return JobCreateResponse(
            job_id=job.job_id,
            project_id=project_id,
            status=job.status,
            message="Processing job created and enqueued successfully."
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Retrieve current processing status, progress percentage, and stage for a job."""
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found."
        )
    return job


@router.post("/jobs/{job_id}/resume", response_model=JobStatusResponse)
async def resume_job(job_id: str, background_tasks: BackgroundTasks):
    """
    Resume an interrupted or failed processing job from its last valid stage checkpoint.
    Skipped videos/stages already completed or cached are not re-processed.
    """
    try:
        job = job_service.resume_job(job_id)
        background_tasks.add_task(
            job_service.execute_background_job,
            job_id=job_id
        )
        return job
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/jobs/{job_id}/stream")
async def stream_job_progress(job_id: str):
    """
    Server-Sent Events (SSE) stream delivering live progress updates as job advances.
    """
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found."
        )

    return StreamingResponse(
        job_service.subscribe_job_stream(job_id),
        media_type="text/event-stream"
    )


@router.get("/cache/status")
async def get_cache_status():
    """Retrieve system cache hit/miss statistics and active processing version."""
    return cache_service.get_cache_stats()
