# VidMind — Phase 4 Milestone 7 Advanced Exports & Offline Experience Architecture
> **Portable, Deterministic, Offline Knowledge Package System**

---

## 1. Overview & Vision
Phase 4 Milestone 7 transforms VidMind knowledge into portable, downloadable, self-describing offline packages.

Users can export any saved Knowledge Item into multiple standardized formats:
- **Markdown Export (`.md`)**: Human-readable structured notes.
- **PDF Export (`.pdf`)**: Formatted document layout.
- **Code Export (`.java`, `.cpp`, `.py`)**: Separate multi-language code files.
- **JSON Knowledge Base (`.json`)**: Machine-readable `schema_version: "1.0"` export.
- **Anki Flashcards (`.csv`)**: CSV for spaced repetition flashcard review.
- **Complete ZIP Knowledge Package (`.zip`)**: Self-contained directory containing `README.md`, `manifest.json` (with SHA256 hashes), `notes/`, `code/`, `sources/`, `evidence/`, and `flashcards/`.

---

## 2. Key Architectural Guarantees

### A. Deterministic Generation (No Gemini or YouTube Reprocessing)
- Exports are 100% derived from saved knowledge snapshots (`knowledge_snapshot`).
- Re-processing YouTube videos or re-querying Gemini during export is strictly forbidden.

### B. Security & Path Traversal Protection
- All filenames and paths are sanitized against path traversal (`../`).
- Secret Exclusion: Verifies that no API keys (`GEMINI_API_KEY`), tokens, or database secrets exist in generated exports.
- Ownership Isolation: All exports enforce `owner_id` verification.

---

## 3. Endpoints Added in Milestone 7

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/library/items/{id}/export/markdown` | `GET` | Download structured Markdown notes |
| `/api/library/items/{id}/export/json` | `GET` | Download versioned JSON knowledge base (`schema_version: "1.0"`) |
| `/api/library/items/{id}/export/pdf` | `GET` | Download formatted PDF document |
| `/api/library/items/{id}/export/anki` | `GET` | Download Anki-compatible CSV flashcards |
| `/api/library/items/{id}/export/zip` | `GET` | Download complete self-describing offline ZIP package |

---

## 4. Scope Boundaries & Limitations (Not in Milestone 7)
- Performance Caching & Background Resumability ➔ **Milestone 8**
- Production Observability & Security Platform ➔ **Milestone 9**
- Final System Integration & E2E Verification ➔ **Milestone 10**
