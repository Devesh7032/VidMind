# VidMind — Phase 4 Milestone 9 Production Security, Reliability & Observability Architecture
> **Hardened Security Boundary, Service-Level Ownership (IDOR Defense), SSRF Protection, Rate Limiting & Observability System**

---

## 1. Overview & Vision
Phase 4 Milestone 9 hardens VidMind into a production-ready, fault-tolerant, diagnosable knowledge platform.

---

## 2. Key Pillars Implemented

### Pillar 1: SECURITY
1. **SSRF & YouTube URL Validation (`SecurityService.validate_youtube_url`)**:
   - Strictly enforces HTTP/HTTPS scheme and public YouTube domains (`youtube.com`, `youtu.be`).
   - Blocks access to `localhost`, `127.0.0.1`, private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), `169.254.169.254` cloud metadata, `file://`, `ftp://`, `data:`, `javascript:`.
2. **Service-Level Ownership Authorization (IDOR Defense)**:
   - Enforces `owner_id` verification across `ProjectService`, `LibraryService`, `ConversationService`, and all REST endpoints.
   - Prevents User B from guessing IDs to access User A's projects, videos, knowledge items, conversations, or exports.
3. **Input Size Bounds & Resource Limits**:
   - `MAX_PROMPT_LENGTH = 10000`
   - `MAX_CHAT_MESSAGE_LENGTH = 4000`
   - `MAX_PAGE_SIZE = 50`
   - `MAX_PLAYLIST_VIDEOS = 50`
4. **Secret Exclusion & Logging Security**:
   - `SecurityService.scrub_secrets` redacts `gemini_api_key_1`, `gemini_api_key_2`, and server secrets from logs, exception messages, and outputs.
5. **Rate Limiting Middleware (`RateLimiterMiddleware`)**:
   - Sliding-window in-memory rate limiter returning HTTP 429 (`RATE_LIMITED`).
6. **Security Headers (`SecurityHeadersMiddleware`)**:
   - Applies `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy`, and `Content-Security-Policy`.

---

### Pillar 2: RELIABILITY
1. **Network Timeouts & Retries**:
   - Applied socket timeouts on `yt-dlp` and Gemini API requests.
2. **Safe Global Error Handling**:
   - `global_exception_handler` returns sanitized JSON errors without exposing raw Python tracebacks or local directory paths to clients.
3. **Graceful Shutdown**:
   - Background tasks and database operations wrap state safely before termination.

---

### Pillar 3: OBSERVABILITY
1. **Request Correlation (`CorrelationIdMiddleware`)**:
   - Generates or propagates `X-Request-ID` header on all API calls and logs.
2. **Operational Metrics (`MetricsService`)**:
   - Collects HTTP request counts, average latencies, cache hit ratios, active/completed/failed job counts, and Gemini 429/fallback events.
3. **Health & Readiness Endpoints**:
   - `GET /health`: Liveness check confirming process is active.
   - `GET /ready`: Readiness check confirming system dependencies are ready.
   - `GET /api/diagnostics`: Protected operational diagnostic endpoint.

---

## 3. Endpoints Added/Hardened in Milestone 9

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `GET /health` | `GET` | Application liveness check endpoint |
| `GET /ready` | `GET` | System readiness check endpoint |
| `GET /api/diagnostics` | `GET` | Protected operational diagnostic status & metrics |
| `POST /api/projects` | `POST` | Create project with SSRF URL check & length bounds |
| `GET /api/projects/{id}` | `GET` | Fetch project with header-based IDOR ownership check |

---

## 4. Scope Boundaries & Limitations (Not in Milestone 9)
- Final System Integration & End-to-End Verification ➔ **Milestone 10**
