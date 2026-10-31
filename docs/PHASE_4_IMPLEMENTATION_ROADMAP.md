# VidMind — Phase 4 Implementation Roadmap
> **10-Milestone Strategic Execution Plan for Production Knowledge Library System**

---

## Roadmap Overview

Phase 4 transforms VidMind into a personal AI knowledge library platform capable of processing full YouTube playlists, extracting multi-language code artifacts, synthesizing cross-video knowledge graphs, providing offline exports (PDF, Anki CSV), searching stored collections, and answering user queries via grounded conversational chat.

---

## Milestone 1: Playlist Ingestion & Multi-Video Job Architecture

### Goal & Scope
Enable VidMind to discover, queue, and process YouTube playlist URLs (`https://youtube.com/playlist?list=...`) preserving video ordering and isolated per-video error handling.

### Dependencies
- Completed Phase 3 single-video ingestion pipeline.

### Technical Components Changed / Added
- `backend/app/services/playlist_service.py` (New): Playlist metadata discovery via `yt-dlp`.
- `backend/app/schemas.py`: `PlaylistIngestionResponse`, `PlaylistJobStatusResponse`.
- `backend/app/services/job_service.py`: Multi-video child job queue & concurrency controller.
- `frontend/src/App.jsx`: Playlist progress indicator UI showing multi-video job state.

### Acceptance Criteria
1. Submitting a YouTube playlist URL creates a parent `PlaylistJob` and child `VideoJob` records for all discovered videos.
2. Videos process concurrently up to `PLAYLIST_MAX_CONCURRENT_VIDEOS`.
3. Failure in one video does not break or cancel remaining playlist videos.
4. SSE stream emits real-time progress for overall playlist completion percentage.

### Risks & Mitigations
- *Risk*: Large playlists (e.g. 50+ videos) exhausting server memory/disk.
- *Mitigation*: Enforce `PLAYLIST_MAX_VIDEO_COUNT=30` limit and stream keyframes to disk instead of memory.

---

## Milestone 2: Advanced Multi-Language Code Extraction & Reconstruction

### Goal & Scope
Extract ALL distinct programming language implementations visible or explained in keyframes (Java, C++, Python, JavaScript), reconstruct progressive typing across frame sequences, and validate syntax without executing code.

### Dependencies
- Milestone 1 (Multi-video job processing).

### Technical Components Changed / Added
- `backend/app/services/ai/gemini_provider.py`: Updated system prompts demanding multi-language separation and `LANGUAGE_UNCERTAIN` handling.
- `backend/app/services/code_reconstruction_service.py` (New): Progressive code state merging across keyframe timestamp windows.
- `backend/app/services/artifact_service.py`: Separates distinct language snippets into individual files (`code/Solution.java`, `code/Solution.cpp`).

### Acceptance Criteria
1. Multi-language video evidence produces separate files in `code/` directory.
2. Unidentifiable code languages are saved as `.txt` files tagged `LANGUAGE_UNCERTAIN`.
3. Progressive code frames are merged into complete runnable code files.
4. AST parsers assign syntax validity status without executing code.

### Risks & Mitigations
- *Risk*: Code editor font/color changes causing false language detection.
- *Mitigation*: Use multi-signal heuristics (file extension in editor tab + keyframe OCR + Gemini vision classification).

---

## Milestone 3: Cross-Video Knowledge Synthesis & Deduplication

### Goal & Scope
Synthesize multimodal evidence across multiple playlist videos into a single unified Intermediate Knowledge Representation (IKR), merging duplicate topics while preserving source citations.

### Dependencies
- Milestone 1 & Milestone 2.

### Technical Components Changed / Added
- `backend/app/services/knowledge_synthesis_service.py` (New): Semantic topic deduplication & graph merging.
- `backend/app/schemas.py`: Multi-source `EvidenceReference` with video IDs and timestamp ranges.

### Acceptance Criteria
1. Overlapping topics across multiple playlist videos are merged into a single topic node.
2. Merged nodes preserve citations to all source videos and timestamps.
3. No duplicate topic headers appear in the final generated Markdown artifact.

### Risks & Mitigations
- *Risk*: Over-aggressive deduplication merging distinct algorithms (e.g., Dijkstra and Bellman-Ford).
- *Mitigation*: Enforce strict semantic similarity threshold ($\ge 0.88$) before merging nodes.

---

## Milestone 4: Persistent Personal Knowledge Library

### Goal & Scope
Build database-backed persistent storage allowing users to organize, browse, and access saved knowledge collections offline.

### Dependencies
- Milestone 3.

### Technical Components Changed / Added
- PostgreSQL schema migration: `collections`, `projects`, `videos`, `topic_nodes`, `code_artifacts`.
- `backend/app/routers/library.py` (New): GET/POST endpoints for browsing saved collections, topics, and artifacts.
- `frontend/src/components/LibraryView.jsx` (New): Library browsing tab.

### Acceptance Criteria
1. Users can create, view, and organize Knowledge Collections.
2. Previously processed projects can be re-opened offline without contacting YouTube.
3. Full artifact packages (Markdown, Code, ZIP) can be re-downloaded at any time.

### Risks & Mitigations
- *Risk*: Database size growth with large text/code payloads.
- *Mitigation*: Index metadata in DB; store large binary/ZIP artifacts in local disk/object storage.

---

## Milestone 5: Search & Knowledge Retrieval System

### Goal & Scope
Implement hybrid search (Dense Vector + Sparse BM25) over the user's stored personal knowledge library.

### Dependencies
- Milestone 4.

### Technical Components Changed / Added
- `backend/app/services/search_service.py` (New): Hybrid vector and keyword search indexer.
- `backend/app/routers/search.py` (New): `GET /api/search?q=query`.

### Acceptance Criteria
1. Queries return exact topic, video source, timestamp, and code snippet matches.
2. Search results rank exact timestamp evidence at the top.
3. Response times remain under 300ms for library collections up to 500 items.

---

## Milestone 6: Conversational Chat Over Saved Knowledge

### Goal & Scope
Enable natural-language chat anchored strictly to the user's saved personal library items with strict grounding guardrails.

### Dependencies
- Milestone 5.

### Technical Components Changed / Added
- `backend/app/services/knowledge_chat_service.py` (New): Context retrieval & grounded Gemini prompt synthesis.
- `backend/app/routers/chat.py` (New): POST `/api/chat` conversational endpoint.

### Acceptance Criteria
1. Answers cite specific source videos, timestamps, and saved artifacts.
2. Questions outside stored library content return explicit ungrounded warnings rather than hallucinations.
3. Users can request code implementations directly in chat.

---

## Milestone 7: Advanced Artifact Export & Offline Experience

### Goal & Scope
Expand artifact export formats to include print-ready PDF documents and Anki flashcard CSV files.

### Dependencies
- Milestone 3 & Milestone 4.

### Technical Components Changed / Added
- `backend/app/services/export_service.py` (New): PDF generation via WeasyPrint/ReportLab & Anki CSV formatter.
- `backend/app/services/artifact_service.py`: Includes PDF and Anki CSV in `export_package.zip`.

### Acceptance Criteria
1. Exporting a project creates valid `knowledge_pack.pdf` and `anki_flashcards.csv`.
2. Anki CSV imports cleanly into Anki desktop/mobile apps.
3. PDF renders mathematical formulas ($\LaTeX$) and syntax-highlighted code blocks clearly.

---

## Milestone 8: Performance, Caching & Resumable Execution

### Goal & Scope
Implement content-hash caching and resumable job execution to eliminate duplicate processing.

### Dependencies
- Milestone 1 through Milestone 4.

### Technical Components Changed / Added
- `backend/app/services/cache_service.py` (New): Content hash calculation (`SHA256(video_id + transcript)`).

### Acceptance Criteria
1. Re-submitting an already processed video URL returns cached evidence instantly.
2. Interrupted playlist jobs resume from the last uncompleted video index.

---

## Milestone 9: Production Security, Reliability & Observability

### Goal & Scope
Implement security guardrails, rate limiting, path traversal validation, and telemetry diagnostics.

### Dependencies
- Milestone 1 through Milestone 8.

### Technical Components Changed / Added
- Security middleware: CORS, URL host validation, API rate limiters.
- Structured JSON logging (zero secret key leakage).

### Acceptance Criteria
1. Path traversal attempts (`../`) are blocked with HTTP 400.
2. Zero API key strings appear in logs, error tracebacks, or API responses.
3. Non-YouTube or malicious URLs are rejected immediately.

---

## Milestone 10: Final Phase 4 Integration & Verification

### Goal & Scope
Conduct complete end-to-end integration testing, regression testing, and verification across all Phase 4 capabilities.

### Dependencies
- Milestones 1 through 9.

### Acceptance Criteria
1. Full test suite passes cleanly.
2. End-to-end playlist test processes multi-video playlist, extracts multi-language code files, synthesizes deduplicated knowledge graph, exports PDF/ZIP/CSV, and enables offline library search and chat.
3. Single-video prompt requests maintain 100% backward compatibility with Phase 3 MVP-1.
