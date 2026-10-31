# VidMind — Phase 4 Milestone 8 Caching & Resumability Architecture
> **Fault-Tolerant, Multi-Tier Caching & Stage Checkpoint Engine**

---

## 1. Overview & Vision
Phase 4 Milestone 8 makes VidMind efficient, fault-tolerant, and resumable.

The system prevents repeating expensive work (Ingestion, Transcripts, Frame Extraction, Vision Analysis, AI Knowledge Reasoning) when underlying video content and processing configurations remain identical.

---

## 2. Key Architecture Components

### A. Multi-Tier Cache Layer (`CacheService`)
Supports 6 explicit cache types:
1. **Video Metadata Cache**: Basic title, duration, channel metadata.
2. **Transcript Cache**: Spoken text segments with start/end timestamps.
3. **Frame Cache**: Extracted keyframe timestamps and image file references.
4. **Vision Analysis Cache**: Multimodal frame OCR and visual element analysis.
5. **AI Knowledge Reasoning Cache**: Intermediate Knowledge Representation (IKR).
6. **Playlist Metadata Cache**: Discovered video items and playlist ordering.

#### Fingerprinting Strategy
- **Content Fingerprint**: SHA256 of `video_id` and raw source content.
- **Processing Fingerprint**: SHA256 of `processing_version` (`m8-v1`), `intent_category`, `user_prompt`, `model`, and `sampling_config`.
- **Atomic Cache Writes**: Only transition to `READY` status when data is fully validated.

### B. Stage & Video-Level Checkpoints (`CheckpointService`)
- **Stage Checkpoint**: Tracks pipeline stages (`INGEST`, `METADATA`, `TRANSCRIPT`, `FRAMES`, `VISION`, `KNOWLEDGE_REASONING`, `ARTIFACT_GENERATION`).
- **Resumability**: `POST /api/jobs/{job_id}/resume` resumes interrupted or failed jobs from their last valid completed stage.
- **Crash Recovery**: `recover_stale_jobs()` recovers jobs after unexpected server crashes or restarts.

---

## 3. Endpoints Added in Milestone 8

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `POST /api/jobs/{job_id}/resume` | `POST` | Resume interrupted or failed job from last valid stage checkpoint |
| `GET /api/cache/status` | `GET` | Retrieve system cache hit/miss statistics and active processing version |

---

## 4. Scope Boundaries & Limitations (Not in Milestone 8)
- Production Security & Reliability Platform ➔ **Milestone 9**
- Distributed Tracing & Observability ➔ **Milestone 9**
- Final Integration & System Verification ➔ **Milestone 10**
