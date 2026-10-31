# VidMind — Project Status & Implementation Guide

## Product Overview
VidMind is a prompt-driven AI video and playlist understanding system that transforms educational video content into structured, reusable, offline-accessible knowledge artifacts (Markdown notes, runnable code files, cheat sheets, flashcards), acts as a Personal AI Knowledge Intelligence Workspace, and executes autonomous multi-agent knowledge workflows.

- **UX Philosophy**: Minimalist, conversational ChatGPT-like interface (`Video/Playlist URL + Natural Language Goal -> Knowledge Artifact -> Autonomous AI Agent Workflows`).
- **Internal Pipeline**: Intent Engine -> Video/Audio Ingestion -> Multimodal Analysis -> Transcript+OCR Fusion -> Intermediate Knowledge Graph -> Validation -> Artifact Exporter -> Personal Knowledge Library -> Search & Retrieval -> Grounded Knowledge Chat -> Advanced Exports & Offline Package Exporter -> Multi-Tier Caching & Stage Checkpoint Resumability Engine -> Production Security Boundary, Rate Limiting & Observability System -> Personal Knowledge Profile -> Gap Detection -> Learning Paths -> Adaptive AI Tutor -> Smart Revision -> Recommendations -> AI Task Planning -> Multi-Agent Orchestrator (Knowledge, Research, Learning, Practice, Content Agents) -> Agent Memory & Execution History.

---

## Current Status & Milestone Tracking (PHASE 6 COMPLETE — 100%)

- [x] **Phase 1 — Product Definition Document**: Complete ([product_definition.md](file:///C:/Users/Devesh/.gemini/antigravity/brain/84d8a109-32f9-4f3d-a5e7-90972ed760f2/product_definition.md)).
- [x] **Phase 2 — Technical Architecture & System Design v2.1**: Complete ([architecture_design.md](file:///C:/Users/Devesh/.gemini/antigravity/brain/84d8a109-32f9-4f3d-a5e7-90972ed760f2/architecture_design.md)).
- [x] **Phase 3 — MVP-1 (Milestones 1–7)**: Completed.
- [x] **Phase 4 — Production Knowledge Platform & Video Intelligence (Milestones 1–10)**: Completed ([PHASE_4_M10_FINAL_VERIFICATION.md](docs/PHASE_4_M10_FINAL_VERIFICATION.md)).
- [x] **Phase 5 — AI Intelligence, Personalization & Knowledge Intelligence (Milestones 1–10)**: Completed ([PHASE_5_FINAL_VERIFICATION.md](docs/PHASE_5_FINAL_VERIFICATION.md)).
- [x] **Phase 6 — Advanced AI Agents & Autonomous Knowledge Workflows**:
  - [x] M1 — AI Task Planning
  - [x] M2 — Knowledge Agent
  - [x] M3 — Research & Source Agent
  - [x] M4 — Learning Agent
  - [x] M5 — Practice & Evaluation Agent
  - [x] M6 — Content Transformation Agent
  - [x] M7 — Multi-Agent Orchestration
  - [x] M8 — Agent Memory & Execution History
  - [x] M9 — Autonomous Personal AI Workspace
  - [x] M10 — Final Phase 6 Verification ([PHASE_6_FINAL_VERIFICATION.md](docs/PHASE_6_FINAL_VERIFICATION.md)).

---

## Repository Layout

```
VidMind/
├── backend/
│   ├── app/
│   │   ├── config.py             # App configuration & environment settings (Dual Gemini Keys + Playlist limits)
│   │   ├── schemas.py            # Pydantic schemas (Collection, KnowledgeItem, Search, Conversation, ChatMessage, IKR, Phase 5 Intelligence, Phase 6 Agents)
│   │   ├── middleware.py         # Middlewares (Correlation ID, Rate Limiter, Security Headers, Global Error Handler)
│   │   ├── main.py               # FastAPI entry point, middleware registration & route dispatch
│   │   ├── routers/
│   │   │   ├── health.py         # GET /health, GET /ready, GET /api/diagnostics
│   │   │   ├── projects.py       # POST /api/projects, GET /api/projects/{id}, GET /api/projects/{id}/playlist/knowledge
│   │   │   ├── jobs.py           # POST /api/projects/{id}/analyze, GET /api/jobs/{id}, POST /api/jobs/{id}/resume, SSE stream, GET /api/cache/status
│   │   │   ├── library.py        # Collections, Save-to-Library & Export API endpoints
│   │   │   ├── search.py         # Global & Collection-scoped Search API endpoints
│   │   │   ├── conversations.py  # Conversational Knowledge Chat API endpoints
│   │   │   ├── intelligence.py   # Phase 5 Personal AI Knowledge & Workspace API endpoints
│   │   │   ├── agents.py         # Phase 6 Autonomous AI Agents & Workflow API endpoints
│   │   │   ├── intents.py        # POST /api/intents/plan (Prompt -> ExtractionPlan)
│   │   │   └── artifacts.py      # GET /api/artifacts/{id}/download (Safe path-sanitized downloads)
│   │   └── services/
│   │       ├── agent_orchestrator_service.py # Phase 6 Multi-Agent Orchestration Engine (Task Planning, Specialized Agents, Loop/Budget Controls, Memory)
│   │       ├── personal_intelligence_service.py # Phase 5 Intelligence Engine (Profile, Gaps, Paths, Tutor, Revision, Recs, Workspace)
│   │       ├── security_service.py            # SSRF protection, YouTube URL validation, input size bounds, secret scrubbing, path safety
│   │       ├── metrics_service.py             # Operational metrics collector (Request count, latency, error count, active jobs, cache hit ratio, Gemini 429/fallbacks)
│   │       ├── project_service.py             # Project store & owner_id IDOR defense manager
│   │       ├── playlist_service.py            # Playlist metadata discovery, ordering & limit validation
│   │       ├── job_service.py                 # Multi-video worker pool, cache hits, stage checkpoints & resume engine
│   │       ├── cache_service.py               # Multi-tier cache service (Metadata, Transcript, Frame, Vision, Knowledge, Playlist)
│   │       ├── checkpoint_service.py          # Stage-level checkpointing, video resumability & crash recovery
│   │       ├── library_service.py             # Collection CRUD, project->library save, idempotency & item retrieval
│   │       ├── search_service.py              # Full-text search engine, deterministic ranking, snippets & filters
│   │       ├── conversation_service.py        # Grounded conversational chat, context builder & session manager
│   │       ├── export_service.py              # Advanced Export Service (Markdown, PDF, Code, JSON, Anki CSV, ZIP package)
│   │       ├── cross_video_synthesis_service.py # Cross-video synthesis, alias deduplication & relationship building
│   │       ├── code_language_classifier.py    # Multi-signal code language classification & multi-region panel detector
│   │       ├── code_reconstruction_service.py # Temporal code reconstruction engine & AST syntax validator
│   │       ├── ingestion_service.py           # Single-video URL validation, SSRF checks, yt-dlp metadata & timestamped transcript
│   │       ├── video_frame_extractor.py       # OpenCV keyframe extraction & perceptual diffing
│   │       ├── multimodal_fusion_service.py   # Transcript-guided windowing, keyframe diffing & transcript+visual fusion
│   │       ├── knowledge_reasoning_service.py # AI Knowledge Reasoning & IKR Synthesis Service
│   │       ├── artifact_service.py            # Markdown rendering, code file packaging, manifest.json & ZIP export
│   │       └── ai/
│   │           ├── base.py                 # LLMProviderInterface (generate_intent_plan, analyze_visual_frame, reason_knowledge_graph, answer_grounded_chat)
│   │           ├── gemini_provider.py      # Gemini 2.5 Flash LLM Provider (Multimodal Vision & Grounded Chat)
│   │           ├── gemini_key_manager.py  # Dual Gemini Keys Failover & Cooldown Manager
│   │           ├── provider_manager.py    # AI Provider Manager Orchestrator
│   │           ├── mock_provider.py        # Deterministic Mock Provider for offline/testing
│   │           └── intent_engine.py        # AI Prompt Intent Engine Service
│   └── tests/
│       ├── test_phase_6_advanced_ai_agents.py       # Phase 6 Autonomous AI Agents & Multi-Agent Orchestration tests
│       ├── test_phase_5_intelligence_personalization.py # Phase 5 Personal Intelligence & AI Workspace tests
│       ├── test_milestone_10_final_integration.py           # E2E system chain, golden path & final regression tests
│       ├── test_milestone_9_security_reliability_observability.py # SSRF, IDOR ownership, secret scrubbing, rate limit & metrics tests
│       ├── test_milestone_8_caching_resumability.py         # Multi-tier caching, checkpoints, resume & recovery tests
│       ├── test_milestone_7_advanced_exports.py            # Markdown, PDF, Code, JSON, Anki & ZIP export tests
│       ├── test_milestone_6_conversational_chat.py          # Grounded chat, citations & code-aware retrieval tests
│       ├── test_milestone_5_search_retrieval.py             # Full-text search, ranking & filter tests
│       ├── test_milestone_4_personal_knowledge_library.py   # Collections CRUD & Save-to-Library tests
│       ├── test_milestone_3_cross_video_synthesis.py        # Cross-video synthesis & deduplication graph tests
│       ├── test_milestone_2_advanced_code_reconstruction.py # Multi-region & temporal code reconstruction tests
│       ├── test_playlist_job_architecture.py      # Playlist discovery, bounded concurrency & failure isolation tests
│       └── test_artifact_generation.py            # Markdown rendering, code files, manifest, ZIP export & end-to-end tests
├── frontend/
│   ├── src/
│   │   ├── App.jsx               # ChatGPT-like UI with Create Knowledge, My Knowledge, Search, Grounded Chat, AI Workspace & Autonomous Agents
│   │   ├── main.jsx              # React DOM entry point
│   │   └── index.css             # Styling & theme setup
│   ├── index.html                # Main HTML document
│   ├── vite.config.js            # Vite dev server configuration with proxy
│   └── package.json              # Dependencies
├── artifacts/                    # Storage directory for generated offline artifacts (projects/{project_id}/)
├── docs/                         # Architectural Documentation
│   ├── PHASE_4_M10_FINAL_VERIFICATION.md         # Phase 4 Final Integration & Production Acceptance Verification Report
│   ├── PHASE_5_FINAL_VERIFICATION.md         # Phase 5 Final Intelligence & Personalization Verification Report
│   └── PHASE_6_FINAL_VERIFICATION.md         # Phase 6 Final Autonomous AI Agents Verification Report
└── PROJECT.md                    # Project tracking document
```

---

## Environment Setup & Run Instructions

### Running Backend
```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Running Backend Automated Tests
```bash
cd backend
pytest
```

### Running Frontend
```bash
cd frontend
npm install
npm run dev
```
Access the application at `http://localhost:5173`.
