import re
import uuid
import yt_dlp
from typing import Dict, List, Optional
from app.config import settings
from app.schemas import (
    PlaylistMetadataResponse,
    PlaylistVideoItem,
    VideoJobStatus
)


class PlaylistService:
    """
    VidMind Playlist Service.
    Discovers YouTube playlist metadata, preserves video order, detects duplicate video IDs,
    and enforces maximum video limits.
    """

    def is_playlist_url(self, url: str) -> bool:
        """Determines if a URL is a YouTube playlist URL."""
        u = (url or "").strip().lower()
        if "list=" in u:
            return True
        if "youtube.com/playlist" in u:
            return True
        return False

    def extract_playlist_metadata(self, playlist_url: str) -> PlaylistMetadataResponse:
        """
        Discovers playlist items using yt-dlp flat playlist extraction without downloading video streams.
        Preserves video ordering and enforces MAX_PLAYLIST_VIDEOS limit.
        """
        url = playlist_url.strip()
        if not self.is_playlist_url(url):
            raise ValueError("URL is not a valid YouTube playlist URL.")

        # Extract playlist ID from URL
        pl_match = re.search(r"list=([a-zA-Z0-9_\-]+)", url)
        playlist_id = pl_match.group(1) if pl_match else f"pl_{uuid.uuid4().hex[:8]}"

        ydl_opts = {
            "extract_flat": "in_playlist",
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            raise ValueError(f"Failed to fetch playlist metadata from YouTube: {str(e)}")

        if not info:
            raise ValueError("Could not retrieve metadata for playlist URL.")

        title = info.get("title") or f"Playlist {playlist_id}"
        uploader = info.get("uploader") or info.get("channel") or "Unknown Channel"
        entries = info.get("entries") or []

        if not entries:
            raise ValueError("The provided playlist contains no accessible videos.")

        # Enforce MAX_PLAYLIST_VIDEOS resource limit
        max_allowed = settings.max_playlist_videos
        if len(entries) > max_allowed:
            raise ValueError(f"Playlist contains {len(entries)} videos, which exceeds the maximum limit of {max_allowed} videos.")

        videos: List[PlaylistVideoItem] = []
        seen_video_ids = set()

        for idx, entry in enumerate(entries, start=1):
            if not entry:
                continue

            v_id = entry.get("id") or entry.get("url") or f"vid_{idx}"
            v_url = entry.get("url")
            if not v_url or not v_url.startswith("http"):
                v_url = f"https://www.youtube.com/watch?v={v_id}"

            v_title = entry.get("title") or f"Video {idx}"
            v_duration = int(entry.get("duration") or 0)

            # Duplicate detection within playlist
            status = VideoJobStatus.PENDING
            error_msg = None
            if v_id in seen_video_ids:
                status = VideoJobStatus.SKIPPED
                error_msg = "Duplicate video ID in playlist."
            else:
                seen_video_ids.add(v_id)

            videos.append(PlaylistVideoItem(
                video_id=v_id,
                source_url=v_url,
                title=v_title,
                position=idx,
                duration_seconds=v_duration,
                status=status,
                error_message=error_msg
            ))

        return PlaylistMetadataResponse(
            playlist_id=playlist_id,
            source_url=url,
            title=title,
            uploader=uploader,
            total_videos=len(videos),
            videos=videos
        )


# Global singleton instance for playlist service
playlist_service = PlaylistService()
