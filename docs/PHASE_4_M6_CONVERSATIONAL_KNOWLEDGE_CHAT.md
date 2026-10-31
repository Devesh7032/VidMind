# VidMind — Phase 4 Milestone 6 Conversational Knowledge Chat Architecture
> **Grounded Conversational Knowledge Chat System**

---

## 1. Overview & Vision
Phase 4 Milestone 6 equips VidMind with a **Grounded Conversational Knowledge Chat System**.

Users can open any saved Knowledge Item or Collection and ask questions naturally. Answers are strictly grounded in retrieved saved knowledge (using M5 retrieval & M4 library snapshots) and generated via Gemini 2.5 Flash with timestamped source citations.

---

## 2. Key Architecture Components

### A. Grounded Retrieval & Gemini Context Builder (`KnowledgeContextBuilder`)
- **Retrieval Before Generation**: For every user question, `KnowledgeContextBuilder` retrieves top matching canonical nodes, code snippets, complexities, and video timestamp evidence before sending the prompt to Gemini.
- **Grounded System Instructions**: Strictly instructs Gemini to answer ONLY using supplied context. If evidence is missing, state clearly *"I couldn't find that information in your saved knowledge"*.
- **Code-Aware Retrieval**: Preserves programming language distinctions (`Solution.java` vs `Solution.cpp`). Never invents or rewrites stored code snippets.

### B. Persistent Conversation Sessions (`ConversationService`)
- **Conversation**: Session model (`id`, `title`, `knowledge_item_id`, `collection_id`, `owner_id`, `created_at`, `updated_at`).
- **Message**: History record (`id`, `conversation_id`, `role`, `content`, `sources`, `created_at`).
- **Follow-Up Questions**: Preserves recent message history for multi-turn conversational context.
- **Session Safety**: Session deletion removes chat history without deleting library items or disk artifacts.

---

## 3. Endpoints Added in Milestone 6

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `POST /api/conversations` | `POST` | Create a grounded conversation session (scoped to item or collection) |
| `GET /api/conversations` | `GET` | List active conversation sessions for user |
| `GET /api/conversations/{id}` | `GET` | Retrieve conversation session details |
| `DELETE /api/conversations/{id}` | `DELETE` | Delete conversation session & message history |
| `GET /api/conversations/{id}/messages` | `GET` | Fetch message history for a conversation |
| `POST /api/conversations/{id}/messages` | `POST` | Post user question, execute M5 retrieval + Gemini, return grounded answer |

---

## 4. Scope Boundaries & Limitations (Not in Milestone 6)
- Advanced Export System (PDF/DOCX/Anki) ➔ **Milestone 7**
- Performance Caching & Background Resumability ➔ **Milestone 8**
- Production Observability & Security Platform ➔ **Milestone 9**
