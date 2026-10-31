# VidMind — Prompt-Driven AI Video Knowledge System (MVP-1)

> **Transform educational videos & playlists into structured, reusable, offline-accessible knowledge artifacts.**

VidMind is a prompt-driven AI platform that accepts a video or playlist URL and a freeform natural-language prompt (e.g. *"Extract all Graph algorithms, code, explanations, and time/space complexities"*), and generates persistent, offline-accessible knowledge artifacts (Markdown notes, runnable code files, cheat sheets).

---

## Quick Start Guide

### 1. Prerequisites
- **Python**: 3.11 or higher
- **Node.js**: 18.0 or higher
- **npm** or **pnpm**
- **OpenCV & yt-dlp**: Automated keyframe extraction

---

### 2. Dual Gemini Keys Configuration (Key 1 Primary + Key 2 Fallback)

VidMind uses a resilient Dual Gemini Key architecture (`gemini-2.5-flash`) managed by `GeminiKeyManager`.

#### Step 1: Configure Environment File
Edit `backend/.env`:
```env
GEMINI_API_KEY_1=your_primary_gemini_api_key
GEMINI_API_KEY_2=your_backup_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
GEMINI_KEY_COOLDOWN_SECONDS=60
```

> ⚠️ **SECURITY WARNING**:  
> Never commit your `.env` file or share API keys publicly. `.env` is ignored by `.gitignore` to prevent secret leakage.

---

### 3. Automatic Gemini Key 1 → Key 2 Failover Architecture

```text
User Video Request
       │
       ▼
GeminiKeyManager (Orchestration Layer)
       │
       ├── Primary: Gemini Key 1
       │       │
       │       ├── SUCCESS ➔ Continue Pipeline
       │       │
       │       └── 429 RATE LIMIT / TIMEOUT / 502
       │                     │
       │                     ▼ (60s Cooldown)
       └── Secondary: Gemini Key 2
               │
               └── SUCCESS ➔ Continue Pipeline (Preserving Evidence)
```

- **Zero Unnecessary Rotation**: Key 1 is used normally. Key 2 is selected only if Key 1 hits a rate limit or timeout.
- **Automatic Cooldown**: Rate-limited keys enter a 60-second cooldown period, after which Key 1 automatically becomes available again.
- **Evidence Preservation**: If Key 1 completes video keyframe analysis and later experiences a rate limit during knowledge reasoning, Key 2 completes the reasoning stage using the preserved multimodal evidence.

---

### 4. Backend Setup & Run

```bash
cd backend

# Create & activate virtual environment
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run FastAPI backend server
uvicorn app.main:app --reload --port 8000
```
- Backend API available at `http://localhost:8000`.
- Interactive Swagger API Docs available at `http://localhost:8000/docs`.

#### Verifying Dual Key Configuration Status
Check the `/api/health` endpoint:
```bash
curl http://localhost:8000/api/health
```
Response:
```json
{
  "status": "ok",
  "service": "VidMind Backend API",
  "environment": "development",
  "gemini_key_1_status": "CONFIGURED",
  "gemini_key_2_status": "CONFIGURED",
  "active_key": "KEY_1",
  "timestamp": "2026-09-01T12:00:00Z"
}
```

#### Running Backend Automated Tests
```bash
cd backend
pytest
```
*Automated unit tests use `MockLLMProvider` deterministically and run completely offline without consuming Gemini API quota.*

---

### 5. Frontend Setup & Run
```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite dev server
npm run dev
```
Frontend interface available at `http://localhost:5173`.

---

## License
MIT License.
