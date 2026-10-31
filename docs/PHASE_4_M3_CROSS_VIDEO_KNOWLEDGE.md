# VidMind — Phase 4 Milestone 3 Cross-Video Knowledge Architecture
> **Cross-Video Knowledge Synthesis & Deduplication Graph**

---

## 1. Overview & Vision
Phase 4 Milestone 3 transforms per-video knowledge representations into **ONE UNIFIED PLAYLIST KNOWLEDGE GRAPH**.

Instead of producing separate, redundant topics for each video in a playlist, VidMind performs candidate generation, alias normalization, semantic deduplication, relationship building, and complete provenance preservation.

---

## 2. Key Architecture Components

### A. Topic Identity & Candidate Generation
- Normalizes topic titles (e.g., "Breadth First Search", "Breadth-First Traversal", "BFS" ➔ canonical topic `BFS`).
- Groups candidates by domain/stem to prevent $O(N^2)$ expensive LLM calls.

### B. Hybrid Semantic Deduplication
- **Alias Match**: Merges strong aliases into a single canonical `KnowledgeNode`.
- **Over-Merge Protection**:
  - `BFS` and `DFS` remain separate.
  - `Dijkstra` and `Bellman-Ford` remain separate.
  - Subtopics (e.g. `DFS for Cycle Detection`) form `SUBTOPIC_OF` or `RELATED_TO` relationships rather than being forcibly merged.

### C. Provenance Preservation (Non-Negotiable)
- Preserves all timestamped evidence references (`playlist_id`, `video_id`, `video_position`, `start_seconds`, `end_seconds`, `observation_type`, `confidence_score`).
- Preserves observation types (`DIRECTLY_OBSERVED`, `RECONSTRUCTED`, `AI_INFERRED`).

### D. Multi-Language Knowledge Association & Code Variants
- Associates multi-language code implementations (e.g., `Solution.java`, `Solution.cpp`, `solution.py`) with the same canonical topic (`BFS`) without merging source code.
- Consolidates identical complexity statements ($O(V+E)$).
- Registers conflicting complexities across videos as `KnowledgeVariant` records with source video attributions.

---

## 3. Endpoints Added in Milestone 3

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `GET /api/projects/{id}/playlist/knowledge` | `GET` | Returns `UnifiedPlaylistKnowledgeGraph` with canonical nodes, relationships, variants, and complete provenance |

---

## 4. Scope Limitations & Clarifications (Not in Milestone 3)
- Personal Knowledge Library Dashboard ➔ **Milestone 4**
- Semantic Search & Vector Retrieval ➔ **Milestone 5**
- Conversational Knowledge Chat ➔ **Milestone 6**
- Advanced Export System (PDF/DOCX/Anki) ➔ **Milestone 7**
