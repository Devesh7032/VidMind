# VidMind — Phase 4 Product Definition Document
> **From Single-Video Artifact Generation to a Personal AI Knowledge Library System**

---

## 1. Executive Summary & Vision

VidMind is a prompt-driven AI video and playlist intelligence platform. It transforms educational videos, lectures, and multi-video playlists into structured, reusable, offline-accessible knowledge artifacts (Markdown lecture notes, runnable multi-language code files, cheat sheets, flashcards, and interactive knowledge graphs).

### Strategic Vision Shift
- **MVP-1 (Phases 1–3)**: Single Video URL + Natural Language Prompt ➔ Offline Knowledge Pack (Markdown + Code + ZIP).
- **Phase 4 Target**: Video / Playlist URL + Natural Language Prompt ➔ **Personal AI Knowledge Library**.

VidMind abstract technical pipeline complexity away from the user. Users simply submit a URL (video or playlist) and state their learning intent. The platform handles video discovery, frame extraction, transcript alignment, multi-language code synthesis, cross-video topic deduplication, storage, search, and conversational retrieval.

---

## 2. Core Product Principles

### 1. User Intent First
The user's natural-language prompt determines:
- **WHAT** knowledge items to extract (e.g., code implementations, complexity analysis, formula references, exam Q&As).
- **HOW** to organize the generated knowledge (e.g., topic hierarchy, chronological timeline, question-answer pairs).
- **WHICH** export artifacts to create (e.g., Markdown, runnable source code files, Anki CSV, PDF).

The internal pipeline automatically determines processing strategy, frame intervals, AI provider failover, and retrieval indexing without exposing technical controls.

### 2. Offline-First Knowledge Ownership
Once a Knowledge Pack or Library Collection is generated:
- Users own the exported artifacts completely.
- Artifacts are 100% usable offline without requiring active internet access, YouTube server availability, or cloud subscription dependencies.

### 3. Absolute Evidence Grounding & Zero Code Ingestion Hallucination
- **No Invented Code**: Every extracted code snippet must be grounded in directly observed keyframes or transcript evidence.
- **Strict Provenance**: Every concept, formula, and code block preserves source video ID, timestamp ranges, confidence scores, and reconstruction type (`DIRECTLY_OBSERVED`, `RECONSTRUCTED`, `AI_INFERRED`).
- **Explicit Uncertainty**: Unidentifiable programming languages are explicitly tagged as `LANGUAGE_UNCERTAIN` rather than guessed.

### 4. Minimalist ChatGPT-Like User Experience
- Clean, clutter-free single input box: `[ Video or Playlist URL ] + [ Natural-Language Prompt ]`.
- No technical configuration forms or model settings visible to end-users.

---

## 3. Key Product Persona & Use Cases

### Primary Personas
1. **Software Engineers & Computer Science Students**:
   - *Goal*: Extract algorithm implementations across multiple languages (Java, C++, Python), time/space complexity explanations, and source timestamps from YouTube tutorials.
2. **Academic & Certification Learners**:
   - *Goal*: Transform long playlist courses (e.g., Operating Systems, DBMS, Machine Learning) into structured revision notes, formula sheets, and Anki flashcards.
3. **Self-Paced Online Researchers**:
   - *Goal*: Build a persistent, searchable personal library of video knowledge that can be queried months later via natural-language chat.

---

## 4. Phase 4 Major Product Capabilities

### A. Playlist & Multi-Video Intelligence
- Accepts playlist URLs (e.g., `https://youtube.com/playlist?list=...`).
- Discovers all playlist items while preserving structural sequence and order.
- Generates a single, cohesive **Knowledge Library Collection** rather than N fragmented documents.

### B. First-Class Multi-Language Code Intelligence
- Extracts ALL distinct programming language implementations visible or explained across keyframes (e.g., Java `Solution.java`, C++ `Solution.cpp`, Python `solution.py`).
- Saves each language to a separate source file in the `code/` artifact directory.
- Clearly labels each language with syntax highlighting and provenance in Markdown and ZIP exports.

### C. Temporal Code Reconstruction
- Assembles progressive code typing across keyframe sequences into complete, runnable code files.
- Uses AST/syntax parsers to verify validity (`VERIFIED`, `UNVERIFIED_FRAGMENT`, `SYNTAX_ERROR`).

### D. Cross-Video Knowledge Synthesis & Deduplication
- Merges duplicate algorithm/concept explanations across multiple playlist videos into unified topic nodes.
- Preserves multi-video timestamp citations (e.g., *BFS algorithm covered in Video 2 @ 03:15 and Video 5 @ 12:40*).

### E. Personal Knowledge Library
- Persistent organizational hierarchy: `Collections ➔ Topics ➔ Sources ➔ Artifacts & Code`.
- Allows users to organize, browse, and access previously generated knowledge offline.

### F. Search & Knowledge Retrieval
- Hybrid search over saved personal library items:
  - *"Show all graph algorithms with O(V+E) time complexity."*
  - *"Where did I learn Tarjan's algorithm?"* ➔ Pinpoints exact video, timestamp, and saved artifact.

### G. Conversational Knowledge Chat
- Interactive chat interface anchored strictly to saved library items.
- Answers user questions, compares concepts, and retrieves relevant code files grounded in verified user evidence.

### H. Multi-Format Artifact Exports
- Automatically generates:
  1. `knowledge_pack.md` (Markdown document)
  2. `code/*` (Separate runnable code files per language)
  3. `export_package.zip` (Complete offline archive)
  4. `Anki_flashcards.csv` (Spaced repetition CSV)
  5. `knowledge_pack.pdf` (Print-ready document)
  6. `manifest.json` (Structured JSON knowledge graph)

---

## 5. Phase 4 Success Criteria

1. **Playlist Processing**: Submitting a 20-video playlist URL produces a single unified Collection within bounds without pipeline failure.
2. **Multi-Language Fidelity**: 100% of distinct programming language implementations in evidence are separated into individual files.
3. **Offline Access**: Generated ZIP archives can be unzipped and navigated offline with zero HTTP requests.
4. **Search Accuracy**: Searching for stored topics yields exact timestamp and document references.
5. **Zero Regression**: Single-video prompt requests function identically to Phase 3 MVP-1.
