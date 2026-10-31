# VidMind — Phase 4 Milestone 2 Advanced Multi-Language Code Architecture
> **Advanced Multi-Language Code Extraction & Temporal Reconstruction**

---

## 1. Overview & Capability
Phase 4 Milestone 2 equips VidMind with **Advanced Multi-Language Code Extraction & Temporal Reconstruction Intelligence**.

When users request code extraction, VidMind automatically detects, separates, reconstructs, and validates **all distinct programming language implementations** visible or explained in the video source.

---

## 2. Key Architecture Components

### A. Multi-Signal Code Language Classifier (`CodeLanguageClassifier`)
- Supports heuristic pattern matching & syntax classification across languages:
  - `cpp`, `java`, `python`, `javascript`, `typescript`, `go`, `rust`, `csharp`, `php`, `ruby`, `swift`, `kotlin`.
- Returns explicit `LANGUAGE_UNCERTAIN` for code with $< 0.40$ confidence.

### B. Multi-Region Code Panel Detection (`CodeRegion`)
- Detects multiple code panels in the same frame (e.g. Java panel on left, C++ panel on right).
- Processes each code region independently without merging different syntax blocks.

### C. Temporal Code Reconstruction Engine (`CodeReconstructionEngine`)
- Assembles progressive typing across timestamped keyframe sequences ($T_1, T_2, \dots, T_n$).
- Groups keyframe observations into language-specific reconstruction tracks (`Java Track`, `C++ Track`, `Python Track`).
- Merges progressive typing versions of the same implementation into a single complete code state.
- Preserves complete source provenance (`video_id`, `start_seconds`, `end_seconds`, `reconstruction_status`, `syntax_validity`).

### D. AST Syntax Validation & Language File Naming
- Validates code syntax using AST parsers and brace balancing without executing code (`VERIFIED`, `UNVERIFIED_FRAGMENT`, `SYNTAX_ERROR`).
- Saves each language implementation to a dedicated file in `code/` (`Solution.java`, `Solution.cpp`, `solution.py`).
- Prevents file collisions for multiple implementations of the same language (`Solution.cpp`, `Solution_2.cpp`).

---

## 3. Scope Limitations (Not in Milestone 2)
- Cross-video knowledge graph deduplication ➔ **Milestone 3**
- Personal Knowledge Library Dashboard ➔ **Milestone 4**
- Semantic Search & Vector Retrieval ➔ **Milestone 5**
- Conversational Chat ➔ **Milestone 6**
- PDF & Anki CSV exports ➔ **Milestone 7**
