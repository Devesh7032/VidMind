# VidMind — Phase 4 Milestone 1 Playlist Architecture
> **Playlist Ingestion & Multi-Video Job Architecture**

---

## 1. Overview & Vision
Phase 4 Milestone 1 extends VidMind from single-video knowledge extraction to **YouTube Playlist Ingestion and Multi-Video Job Architecture**.

Submitting a playlist URL (e.g. `https://www.youtube.com/playlist?list=...`) creates a playlist project and multi-video background job, processing child videos with bounded concurrency and failure isolation.

---

## 2. Key Architecture Components

### A. Playlist URL Validation & Metadata Ingestion (`PlaylistService`)
- Supports YouTube playlist URLs (`playlist?list=...`, `watch?v=...&list=...`).
- Uses `yt-dlp` flat playlist extraction without downloading video streams immediately.
- Preserves video order and position (`position: 1, 2, ...`).
- Enforces `MAX_PLAYLIST_VIDEOS=50` resource limit.
- Detects duplicate video IDs within a playlist and flags them as `SKIPPED`.

### B. Multi-Video Job Queue & Bounded Concurrency (`JobService`)
- Configurable worker pool concurrency (`MAX_CONCURRENT_VIDEOS=2`).
- Child video jobs inherit the parent project's natural language `user_prompt` and `extraction_plan`.
- **Failure Isolation**: One failed video does NOT cancel or fail the remaining playlist job.
- Final Playlist Job States:
  - `COMPLETED`: All videos succeeded.
  - `PARTIALLY_FAILED`: At least 1 video succeeded and some failed.
  - `FAILED`: All videos failed.

### C. Live SSE Progress Stream
- Emits real-time progress events:
  ```json
  {
    "job_id": "job_123",
    "status": "PROCESSING_VIDEO",
    "progress_percent": 60,
    "is_playlist": true,
    "completed_videos": 3,
    "total_videos": 5,
    "current_video_title": "2. BFS Algorithm"
  }
  ```

---

## 3. Endpoints Added in Milestone 1

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `POST /api/projects` | `POST` | Accepts single video OR playlist URLs (`is_playlist: true`) |
| `GET /api/projects/{id}/playlist` | `GET` | Returns playlist metadata and ordered video list |
| `POST /api/projects/{id}/analyze` | `POST` | Enqueues background processing job (single video or playlist) |
| `GET /api/jobs/{id}/stream` | `GET` | SSE stream for live playlist or single-video progress updates |

---

## 4. Scope Limitations (Not in Milestone 1)
- Cross-video knowledge graph deduplication ➔ **Milestone 3**
- Personal Knowledge Library Dashboard ➔ **Milestone 4**
- Semantic Search & Vector Retrieval ➔ **Milestone 5**
- Conversational Chat ➔ **Milestone 6**
- PDF & Anki CSV exports ➔ **Milestone 7**
