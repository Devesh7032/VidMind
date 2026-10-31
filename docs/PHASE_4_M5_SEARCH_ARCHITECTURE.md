# VidMind — Phase 4 Milestone 5 Search & Retrieval Architecture
> **Search & Retrieval System**

---

## 1. Overview & Vision
Phase 4 Milestone 5 provides VidMind with a **Search & Retrieval System**.

Users can instantly search their personal knowledge library across saved knowledge item titles, topic names, concepts, definitions, code implementations, programming languages, and video source metadata.

Search operations are 100% deterministic (never using external LLM calls or vector databases), execute with relevance-based scoring, term snippet highlighting, and respect strict user `owner_id` isolation boundaries.

---

## 2. Key Architecture Components

### A. Deterministic Search Service (`SearchService`)
- **Query Processing**: Normalizes and parses input terms without LLM calls.
- **Weighted Relevance Scoring**:
  - Exact Title Match: `1.00`
  - Partial Title Match: `0.90`
  - Topic / M3 Alias Match: `0.85`
  - Concept / Definition Match: `0.75`
  - Code Content / Programming Language Match: `0.65`
  - Source Metadata Match: `0.50`
  - Secondary Ordering: `updated_at DESC`
- **Contextual Snippets & Term Highlighting**: Extracts a 160-character contextual snippet and wraps matched query terms in HTML `<mark>` tags.
- **Filtering**: Supports collection scoping (`collection_id`), programming language filtering (`language`), and topic title filtering (`topic`).
- **Pagination**: Supports page slicing (`page`, `page_size`, `has_next`).

### B. Index Synchronization & Security
- Directly queries live library data, guaranteeing zero stale search results on creation, update, or deletion.
- Enforces `owner_id` scoping to prevent cross-user data leakage.

---

## 3. Endpoints Added in Milestone 5

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `GET /api/search` | `GET` | Global search over saved knowledge library items with filters & pagination |
| `GET /api/collections/{id}/search` | `GET` | Collection-scoped search over items in a specific collection |

---

## 4. Scope Boundaries & Limitations (Not in Milestone 5)
- Conversational Knowledge Chat ➔ **Milestone 6**
- Vector Embeddings / Semantic Chatbot ➔ **Milestone 6**
- Advanced Exports (PDF/DOCX/Anki) ➔ **Milestone 7**
