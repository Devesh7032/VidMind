# VidMind — Phase 4 Technical Architecture Document
> **Production-Grade Personal AI Knowledge Library System Architecture**

---

## 1. System Architecture Overview

VidMind Phase 4 expands the MVP-1 single-video pipeline into a multi-video, playlist-aware, offline-first personal knowledge library engine.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   React Frontend                                       │
│          (ChatGPT-Like UI / Personal Library / Search / Knowledge Chat)               │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ HTTP REST / SSE Stream
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   FastAPI Backend                                      │
│                                                                                        │
│  ┌───────────────────────────┐  ┌───────────────────────────┐  ┌────────────────────┐ │
│  │   Playlist & Video        │  │     AI Provider Manager   │  │   Library Store    │ │
│  │   Ingestion Engine        │  │   (Gemini Key 1 & Key 2)  │  │   & Indexer        │ │
│  └─────────────┬─────────────┘  └─────────────┬─────────────┘  └─────────┬──────────┘ │
│                │                              │                          │            │
│                ▼                              ▼                          ▼            │
│  ┌───────────────────────────┐  ┌───────────────────────────┐  ┌────────────────────┐ │
│  │ Multimodal Vision Fusion  │  │ Multi-Language Code       │  │ Hybrid Search &    │ │
│  │ (OpenCV + yt-dlp)         │  │ Reconstruction Engine     │  │ Knowledge Chat     │ │
│  └───────────────────────────┘  └───────────────────────────┘  └────────────────────┘ │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               Storage & Storage Layer                                  │
│  ┌───────────────────────────┐  ┌───────────────────────────┐  ┌────────────────────┐ │
│  │ PostgreSQL Relational DB  │  │ Local Offline Disk Store  │  │ Vector / BM25      │ │
│  │ (Knowledge Graphs/Library)│  │ (Markdown, Code, ZIP, PDF)│  │ Search Index       │ │
│  └───────────────────────────┘  └───────────────────────────┘  └────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Playlist Ingestion & Batch Processing Architecture

```
Playlist URL ➔ Playlist Discovery ➔ Video Batch Queue ➔ Async Worker Pool ➔ Progress SSE ➔ Synthesis
```

### Components
1. **Playlist Metadata Collector**: Uses `yt-dlp` flat-playlist extraction (`--flat-playlist --dump-single-json`) to collect video IDs, titles, indexes, and durations without downloading video streams immediately.
2. **Playlist Job Manager**: Creates a parent `PlaylistJob` and child `VideoJob` records in PostgreSQL.
3. **Resumable Worker Pool**:
   - Executes video processing concurrently with configurable concurrency limits (`PLAYLIST_MAX_CONCURRENT_VIDEOS=2`).
   - If Video 4 fails, its state is marked `FAILED_RETRYABLE`. Videos 1–3 and 5+ continue processing uninterrupted.
   - Resuming a interrupted playlist job skips already completed video outputs.

---

## 3. Dual Gemini Key Orchestration Architecture

VidMind strictly utilizes **Google Gemini 2.5 Flash** as its AI foundation with a Dual-Key failover strategy (`GeminiKeyManager`).

```
                              AI Provider Manager
                                       │
                      ┌────────────────┴────────────────┐
                      ▼                                 ▼
              Gemini Key 1 (Primary)            Gemini Key 2 (Fallback)
              [Active Slot: KEY_1]              [Active Slot: KEY_2]
                      │                                 │
                      └────────────────┬────────────────┘
                                       │
                                       ▼
                              Google Gemini API
```

### Failover & Cooldown Mechanics
1. **Primary Selection**: Requests default to `GEMINI_API_KEY_1`.
2. **Quota / Rate Limit Interception**: Upon HTTP 429 or `RESOURCE_EXHAUSTED` responses, `GeminiLLMProvider` marks `KEY_1` into cooldown (`GEMINI_KEY_COOLDOWN_SECONDS=60`) and immediately redirects pending requests to `GEMINI_API_KEY_2`.
3. **Cooldown Expiration**: Once 60 seconds elapse, `GeminiKeyManager` automatically restores `KEY_1` as primary without interrupting running jobs.
4. **Zero Key Rotation**: Keys are not rotated when `KEY_1` is operating normally.

---

## 4. Multi-Language Code Reconstruction Engine

### Reconstruction Pipeline

```
Keyframe Sequence ➔ Code Region Crop ➔ Language Detection ➔ Diff Merging ➔ AST Parser ➔ File Exporter
```

1. **Detection & Separation**:
   - Analyzes visual keyframes for visible code editor windows.
   - Detects programming language (`cpp`, `java`, `python`, `javascript`, `html`, `language_uncertain`).
   - Keeps distinct language implementations strictly separated into individual `CodeSnippet` models.
2. **Temporal Alignment & State Merging**:
   - Merges progressive typing across sequential frames ($T_1, T_2, \dots, T_n$) into a single unified code state.
3. **AST & Syntax Validation**:
   - Validates code syntax using language parsers (e.g., Python `ast.parse`, tree-sitter for C++/Java).
   - Assigns `syntax_validity`: `VERIFIED`, `UNVERIFIED_FRAGMENT`, or `SYNTAX_ERROR`.
4. **Output Generation**:
   - Saves `code/Solution.java`, `code/Solution.cpp`, `code/solution.py` into project artifacts.

---

## 5. Unified Knowledge Graph Synthesizer

The Knowledge Synthesizer aggregates evidence across single or multiple videos into an **Intermediate Knowledge Representation (IKR)**.

```
Video 1 Evidence ──┐
Video 2 Evidence ──┼──> Deduplication & Topic Alignment ──> Unified IKR ──> Library Node
Video N Evidence ──┘
```

### Topic Deduplication Algorithm
1. Extracts topic titles and concept summaries from all processed videos.
2. Computes pairwise semantic similarity across topic nodes.
3. Merges overlapping nodes while preserving multi-video timestamp citations:
   ```json
   "evidence_references": [
     {"video_id": "vid_01", "start_seconds": 120.0, "end_seconds": 240.0},
     {"video_id": "vid_05", "start_seconds": 45.0, "end_seconds": 110.0}
   ]
   ```

---

## 6. Database Evolution Plan (PostgreSQL Schema)

```sql
-- Collections Table (User Knowledge Folders)
CREATE TABLE collections (
    collection_id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Projects / Ingestion Jobs
CREATE TABLE projects (
    project_id VARCHAR(64) PRIMARY KEY,
    collection_id VARCHAR(64) REFERENCES collections(collection_id) ON DELETE SET NULL,
    source_url TEXT NOT NULL,
    is_playlist BOOLEAN DEFAULT FALSE,
    user_prompt TEXT NOT NULL,
    intent_category VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Video Metadata Cache
CREATE TABLE videos (
    video_id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    duration_seconds DOUBLE PRECISION NOT NULL,
    channel_name VARCHAR(255),
    thumbnail_url TEXT,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Playlist Items Mapping
CREATE TABLE playlist_items (
    playlist_id VARCHAR(64) NOT NULL,
    video_id VARCHAR(64) REFERENCES videos(video_id),
    sequence_order INT NOT NULL,
    PRIMARY KEY (playlist_id, video_id)
);

-- Fused Evidence Table
CREATE TABLE evidence (
    evidence_id VARCHAR(64) PRIMARY KEY,
    video_id VARCHAR(64) REFERENCES videos(video_id),
    start_seconds DOUBLE PRECISION NOT NULL,
    end_seconds DOUBLE PRECISION NOT NULL,
    transcript_text TEXT,
    visual_description TEXT,
    visible_code_text TEXT,
    observation_type VARCHAR(64) NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL
);

-- Knowledge Topic Nodes
CREATE TABLE topic_nodes (
    node_id VARCHAR(64) PRIMARY KEY,
    project_id VARCHAR(64) REFERENCES projects(project_id) ON DELETE CASCADE,
    topic_title VARCHAR(255) NOT NULL,
    concept_summary TEXT NOT NULL,
    time_complexity VARCHAR(64),
    space_complexity VARCHAR(64)
);

-- Multi-Language Code Artifacts Table
CREATE TABLE code_artifacts (
    code_id VARCHAR(64) PRIMARY KEY,
    node_id VARCHAR(64) REFERENCES topic_nodes(node_id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    language VARCHAR(64) NOT NULL,
    code_content TEXT NOT NULL,
    syntax_validity VARCHAR(64) NOT NULL,
    reconstruction_status VARCHAR(64) NOT NULL
);
```

---

## 7. Search & Retrieval Architecture

VidMind implements a **Hybrid Search Engine**:
- **Sparse BM25 Keyword Search**: For exact code identifiers, syntax terms, function names, and technical terms.
- **Dense Vector Embeddings**: For semantic queries (*"algorithms for finding shortest path in weighted graphs"*).
- **Reciprocal Rank Fusion (RRF)**: Merges dense and sparse search results, ranking exact evidence matches first.

---

## 8. Conversational Knowledge Chat Engine

Allows natural-language dialogue over the user's saved library items.

```
User Query ➔ Library Context Retrieval ➔ Grounding Verification ➔ Gemini Reasoning ➔ Response with Citations
```

- **Strict Grounding Guardrail**: The system prompt forces answers to be cited strictly from stored library nodes and evidence references. If an answer is not present in the user's saved library, VidMind explicitly states: *"This information is not covered in your saved video knowledge collection."*

---

## 9. Storage & Caching Layer

### Deterministic Video Content Hash Caching
Before downloading or extracting frames for a video URL:
1. Calculates content hash: `SHA256(video_id + transcript_text)`.
2. If hash match exists in PostgreSQL `videos` and `evidence` tables:
   - Skips `yt-dlp` video download and frame extraction entirely.
   - Reuses stored multimodal evidence, reducing processing time by ~85%.

---

## 10. Production Security & Trust Boundaries

1. **Zero Untrusted Code Execution**: Extracted code snippets are strictly parsed via static AST engines. Code is never executed on the host server.
2. **Path Traversal Guardrails**: All file reads/writes are restricted to `artifacts/projects/{project_id}/` using `os.path.abspath` boundary validation.
3. **Secret Protection**: API keys (`GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`) are loaded strictly in FastAPI backend settings and never exposed in REST responses, logs, or frontend bundles.
