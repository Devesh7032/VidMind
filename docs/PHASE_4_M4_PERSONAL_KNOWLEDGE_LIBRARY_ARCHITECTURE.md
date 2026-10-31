# VidMind — Phase 4 Milestone 4 Personal Knowledge Library Architecture
> **Personal Knowledge Library System**

---

## 1. Overview & Vision
Phase 4 Milestone 4 equips VidMind with a **Personal Knowledge Library System**.

Users process video or playlist content once and permanently save the resulting unified knowledge graph, timestamped evidence, multi-language code files, and downloadable artifacts into structured Collections (e.g., *DSA*, *AI / ML*, *Web Development*, *System Design*).

Saved library items can be opened, browsed, and downloaded at any time without reprocessing the source content.

---

## 2. Key Architecture Components

### A. Persistent Collections & Knowledge Items (`LibraryService`)
- **Collection**: Logical folder (`id`, `name`, `description`, `owner_id`, `item_count`, `created_at`, `updated_at`).
- **KnowledgeItem**: Saved knowledge snapshot (`id`, `collection_id`, `project_id`, `title`, `source_url`, `is_playlist`, `knowledge_snapshot`, `artifact_references`, `created_at`, `updated_at`).

### B. Duplicate Save Protection (Idempotency)
- Attempting to save the same completed project to the same collection twice does NOT create accidental duplicate records (`status: "already_saved"`).

### C. Complete Provenance & Multi-Language Preservation
- Preserves all video IDs, playlist IDs, timestamp ranges, observation types, and confidence scores.
- Keeps multi-language code snippets distinct (`Solution.java`, `Solution.cpp`, `solution.py`).
- Maintains links to existing downloadable artifact files on disk (`.md`, `.py`, `.zip`).

### D. Safe Collection Deletion & Ownership Boundaries
- Deleting a collection removes the library association while preserving original project records and disk artifacts.
- Enforces `owner_id` isolation to prevent cross-user data leakage.

---

## 3. Endpoints Added in Milestone 4

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `POST /api/collections` | `POST` | Create a new collection category |
| `GET /api/collections` | `GET` | List all user collections |
| `GET /api/collections/{id}` | `GET` | Retrieve collection details |
| `PATCH /api/collections/{id}` | `PATCH` | Rename or update collection description |
| `DELETE /api/collections/{id}` | `DELETE` | Safely delete collection |
| `GET /api/collections/{id}/items` | `GET` | List knowledge items in collection |
| `POST /api/projects/{id}/save-to-library` | `POST` | Save completed project to collection (Idempotent) |
| `GET /api/library/items` | `GET` | List all saved library items across collections |
| `GET /api/library/items/{id}` | `GET` | Retrieve full saved knowledge item details |

---

## 4. Scope Limitations & Clarifications (Not in Milestone 4)
- Search & Vector Retrieval ➔ **Milestone 5**
- Conversational Knowledge Chat ➔ **Milestone 6**
- Advanced Export System (PDF/DOCX/Anki) ➔ **Milestone 7**
