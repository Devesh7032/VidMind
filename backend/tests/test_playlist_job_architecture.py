import pytest
import asyncio
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.schemas import (
    ProjectCreateRequest,
    ProjectResponse,
    ProjectStatus,
    VideoJobStatus,
    PlaylistJobStatus,
    PlaylistMetadataResponse,
    PlaylistVideoItem
)
from app.services.playlist_service import PlaylistService, playlist_service
from app.services.project_service import ProjectService, project_service
from app.services.job_service import JobService, job_service

client = TestClient(app)


def test_playlist_url_detection_and_validation():
    """Requirement 22.1 & 22.2: Valid playlist URLs are accepted, invalid/unsupported URLs are rejected."""
    # Valid playlist URLs
    r1 = ProjectCreateRequest(
        source_url="https://www.youtube.com/playlist?list=PLgUwDviBIf0oF6QL8m22w1hIDC1vJ_BHz",
        user_prompt="Extract all graph algorithms"
    )
    assert r1.source_url.startswith("https://")

    r2 = ProjectCreateRequest(
        source_url="https://www.youtube.com/watch?v=qrAub5z8FeA&list=PLgUwDviBIf0oF6QL8m22w1hIDC1vJ_BHz",
        user_prompt="Extract graph code"
    )
    assert r2.source_url.startswith("https://")

    # Invalid URL domain
    with pytest.raises(ValueError, match="Unsupported source domain"):
        ProjectCreateRequest(
            source_url="https://malicious-domain.com/playlist",
            user_prompt="Extract code"
        )


def test_playlist_metadata_extraction_and_ordering():
    """Requirement 22.4 & 22.5: Playlist metadata discovers videos and preserves position ordering."""
    mock_raw_info = {
        "title": "Graph Algorithms Course",
        "uploader": "TakeUForward",
        "entries": [
            {"id": "vid1", "url": "https://www.youtube.com/watch?v=vid1", "title": "1. Intro to Graphs", "duration": 300},
            {"id": "vid2", "url": "https://www.youtube.com/watch?v=vid2", "title": "2. BFS Algorithm", "duration": 450},
            {"id": "vid3", "url": "https://www.youtube.com/watch?v=vid3", "title": "3. DFS Algorithm", "duration": 600}
        ]
    }

    with patch("yt_dlp.YoutubeDL.extract_info", return_value=mock_raw_info):
        meta = playlist_service.extract_playlist_metadata("https://www.youtube.com/playlist?list=PL123")
        assert meta.title == "Graph Algorithms Course"
        assert meta.total_videos == 3
        assert meta.videos[0].video_id == "vid1"
        assert meta.videos[0].position == 1
        assert meta.videos[1].video_id == "vid2"
        assert meta.videos[1].position == 2
        assert meta.videos[2].video_id == "vid3"
        assert meta.videos[2].position == 3


def test_playlist_max_video_limit_enforced():
    """Requirement 22.6: Playlist exceeding MAX_PLAYLIST_VIDEOS limit raises ValueError."""
    mock_entries = [{"id": f"v_{i}", "url": f"https://youtube.com/watch?v=v_{i}", "title": f"Vid {i}"} for i in range(55)]
    mock_raw_info = {"title": "Huge Course", "entries": mock_entries}

    with patch("yt_dlp.YoutubeDL.extract_info", return_value=mock_raw_info):
        with pytest.raises(ValueError, match="exceeds the maximum limit of 50 videos"):
            playlist_service.extract_playlist_metadata("https://www.youtube.com/playlist?list=PL123")


def test_duplicate_video_ids_detected_and_skipped():
    """Requirement 22.8: Duplicate video IDs in a playlist are marked SKIPPED."""
    mock_raw_info = {
        "title": "Duplicate Test Playlist",
        "entries": [
            {"id": "vid1", "url": "https://youtube.com/watch?v=vid1", "title": "Video 1"},
            {"id": "vid1", "url": "https://youtube.com/watch?v=vid1", "title": "Video 1 Duplicate"}
        ]
    }

    with patch("yt_dlp.YoutubeDL.extract_info", return_value=mock_raw_info):
        meta = playlist_service.extract_playlist_metadata("https://www.youtube.com/playlist?list=PL123")
        assert len(meta.videos) == 2
        assert meta.videos[0].status == VideoJobStatus.PENDING
        assert meta.videos[1].status == VideoJobStatus.SKIPPED
        assert "Duplicate" in meta.videos[1].error_message


def test_playlist_project_and_job_creation():
    """Requirement 22.9, 22.10, 22.11: Creating a playlist project initializes is_playlist=True and creates job."""
    mock_raw_info = {
        "title": "Graph Algorithms",
        "entries": [
            {"id": "v1", "url": "https://youtube.com/watch?v=v1", "title": "BFS"},
            {"id": "v2", "url": "https://youtube.com/watch?v=v2", "title": "DFS"}
        ]
    }

    with patch("yt_dlp.YoutubeDL.extract_info", return_value=mock_raw_info):
        proj = project_service.create_project(
            ProjectCreateRequest(
                source_url="https://www.youtube.com/playlist?list=PL123",
                user_prompt="Extract all graph code"
            )
        )

        assert proj.is_playlist is True
        assert proj.playlist_metadata.total_videos == 2

        job = job_service.create_job(proj.project_id)
        assert job.is_playlist is True
        assert job.total_videos == 2


@pytest.mark.asyncio
async def test_playlist_failure_isolation_partially_failed_state():
    """Requirement 22.14 & 22.15: Failure isolation. If 1 video succeeds and 1 fails, status is PARTIALLY_FAILED."""
    mock_raw_info = {
        "title": "Failure Isolation Test",
        "entries": [
            {"id": "v1", "url": "https://youtube.com/watch?v=v1", "title": "Good Video"},
            {"id": "v2", "url": "https://youtube.com/watch?v=v2", "title": "Bad Video"}
        ]
    }

    with patch("yt_dlp.YoutubeDL.extract_info", return_value=mock_raw_info):
        proj = project_service.create_project(
            ProjectCreateRequest(
                source_url="https://www.youtube.com/playlist?list=PL123",
                user_prompt="Extract code"
            )
        )
        job = job_service.create_job(proj.project_id)

    async def mock_video_pipeline(child_pid, source_url, title, delay_step=0.01):
        if "v2" in child_pid or "v2" in source_url:
            raise RuntimeError("Video download timed out")
        return {"title": title, "artifacts_count": 2, "generated_files": ["knowledge_pack.md", "code/solution.py"]}

    with patch.object(job_service, "_process_single_video_pipeline", side_effect=mock_video_pipeline):
        await job_service.execute_background_job(job.job_id, delay_step=0.001)

    updated_job = job_service.get_job(job.job_id)
    assert updated_job.status == ProjectStatus.PARTIALLY_FAILED
    assert updated_job.completed_videos == 1
    assert updated_job.failed_videos == 1


@pytest.mark.asyncio
async def test_single_video_project_regression():
    """Requirement 22.20: Single video processing still works 100% without regression."""
    proj = project_service.create_project(
        ProjectCreateRequest(
            source_url="https://www.youtube.com/watch?v=qrAub5z8FeA",
            user_prompt="Extract graph code"
        )
    )
    assert proj.is_playlist is False

    job = job_service.create_job(proj.project_id)

    async def mock_single_pipeline(pid, url, title, delay_step=0.01):
        return {"title": title, "artifacts_count": 2, "generated_files": ["knowledge_pack.md"]}

    with patch.object(job_service, "_process_single_video_pipeline", side_effect=mock_single_pipeline):
        await job_service.execute_background_job(job.job_id, delay_step=0.001)

    updated_job = job_service.get_job(job.job_id)
    assert updated_job.status == ProjectStatus.COMPLETED
    assert updated_job.progress_percent == 100
