import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from app.schemas import (
    ConversationCreateRequest,
    ConversationResponse,
    PostMessageRequest,
    ChatMessageResponse,
    CitationSource
)
from app.services.library_service import library_service
from app.services.search_service import search_service
from app.services.ai.provider_manager import provider_manager


class KnowledgeContextBuilder:
    """
    VidMind Knowledge Context Builder.
    Retrieves and bounds relevant knowledge context, code snippets, timestamps,
    and citations from M5 search or M4 library item snapshots before sending to Gemini.
    """

    def build_context(
        self,
        query: str,
        owner_id: str,
        knowledge_item_id: Optional[str] = None,
        collection_id: Optional[str] = None
    ) -> Tuple[str, List[CitationSource]]:
        citations: List[CitationSource] = []
        context_parts: List[str] = []

        # 1. Direct Knowledge Item Scoped Retrieval
        if knowledge_item_id:
            item = library_service.get_knowledge_item(knowledge_item_id, owner_id=owner_id)
            if item:
                context_parts.append(f"KNOWLEDGE ITEM TITLE: {item.title}")
                context_parts.append(f"SOURCE URL: {item.source_url}")
                
                snapshot = item.knowledge_snapshot or {}
                nodes = snapshot.get("canonical_nodes") or snapshot.get("topic_nodes") or []
                
                for n_idx, node in enumerate(nodes):
                    if isinstance(node, dict):
                        t_title = node.get("topic_title", "Topic")
                        summary = node.get("concept_summary", "")
                        context_parts.append(f"\n--- TOPIC #{n_idx+1}: {t_title} ---")
                        if summary:
                            context_parts.append(f"CONCEPT SUMMARY: {summary}")

                        complexities = node.get("complexities") or {}
                        if isinstance(complexities, dict):
                            t_comp = complexities.get("time_complexity")
                            s_comp = complexities.get("space_complexity")
                            c_exp = complexities.get("explanation")
                            if t_comp or s_comp:
                                context_parts.append(f"COMPLEXITY: Time={t_comp or 'N/A'}, Space={s_comp or 'N/A'}. {c_exp or ''}")

                        code_snippets = node.get("code_snippets") or []
                        for cs in code_snippets:
                            if isinstance(cs, dict):
                                lang = cs.get("language", "code")
                                fname = cs.get("filename", "solution")
                                code_txt = cs.get("code_content", "")
                                context_parts.append(f"\nCODE SNIPPET ({fname}, {lang}):\n```{lang}\n{code_txt}\n```")

                        evidence_refs = node.get("evidence_references") or []
                        for ev in evidence_refs:
                            if isinstance(ev, dict):
                                v_id = ev.get("video_id", "unknown_video")
                                s_sec = ev.get("start_seconds", 0.0)
                                mins = int(s_sec // 60)
                                secs = int(s_sec % 60)
                                ts_str = f"{mins:02d}:{secs:02d}"
                                citations.append(CitationSource(
                                    source_id=f"cit_{v_id}_{int(s_sec)}",
                                    video_id=v_id,
                                    timestamp=ts_str,
                                    title=f"{t_title} ({item.title})",
                                    evidence_id=ev.get("evidence_id")
                                ))

        # 2. Search / Collection Scoped Retrieval if knowledge_item_id not scoped or context empty
        if not context_parts:
            search_res = search_service.search(
                query=query,
                owner_id=owner_id,
                collection_id=collection_id,
                page_size=5
            )

            if search_res.total == 0:
                return "NO_RELEVANT_KNOWLEDGE_FOUND", []

            for s_item in search_res.results:
                context_parts.append(f"\nMATCHED ITEM: {s_item.title} (Collection: {s_item.collection_name})")
                context_parts.append(f"SNIPPET: {s_item.snippet}")
                if s_item.matched_topics:
                    context_parts.append(f"TOPICS: {', '.join(s_item.matched_topics)}")
                if s_item.matched_languages:
                    context_parts.append(f"LANGUAGES: {', '.join(s_item.matched_languages)}")
                
                citations.append(CitationSource(
                    source_id=f"cit_{s_item.knowledge_item_id}",
                    title=f"{s_item.title} ({s_item.collection_name})"
                ))

        bounded_context = "\n".join(context_parts)
        return bounded_context, citations


class ConversationService:
    """
    VidMind Grounded Conversational Knowledge Chat Service.
    Manages persistent chat sessions, message history, M5 retrieval integration,
    grounded Gemini answer generation, and timestamped source citations.
    """

    def __init__(self):
        # In-memory stores (backed by SQLite/PostgreSQL schema in production)
        # conversation_id -> conversation dict
        self._conversations: Dict[str, Dict[str, Any]] = {}
        # conversation_id -> list of message dicts
        self._messages: Dict[str, List[Dict[str, Any]]] = {}

        self.context_builder = KnowledgeContextBuilder()

    def create_conversation(self, request: ConversationCreateRequest) -> ConversationResponse:
        owner_id = request.owner_id or "default_user"
        c_id = f"conv_{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc)

        title = request.title or "Knowledge Chat Session"
        if request.knowledge_item_id:
            item = library_service.get_knowledge_item(request.knowledge_item_id, owner_id=owner_id)
            if item:
                title = f"Chat: {item.title}"

        record = {
            "conversation_id": c_id,
            "title": title,
            "knowledge_item_id": request.knowledge_item_id,
            "collection_id": request.collection_id,
            "owner_id": owner_id,
            "created_at": now,
            "updated_at": now
        }

        self._conversations[c_id] = record
        self._messages[c_id] = []

        return ConversationResponse(
            conversation_id=c_id,
            title=title,
            knowledge_item_id=request.knowledge_item_id,
            collection_id=request.collection_id,
            owner_id=owner_id,
            message_count=0,
            created_at=now,
            updated_at=now
        )

    def list_conversations(self, owner_id: str = "default_user") -> List[ConversationResponse]:
        results = []
        for rec in self._conversations.values():
            if rec["owner_id"] == owner_id:
                msg_count = len(self._messages.get(rec["conversation_id"], []))
                results.append(ConversationResponse(
                    conversation_id=rec["conversation_id"],
                    title=rec["title"],
                    knowledge_item_id=rec["knowledge_item_id"],
                    collection_id=rec["collection_id"],
                    owner_id=rec["owner_id"],
                    message_count=msg_count,
                    created_at=rec["created_at"],
                    updated_at=rec["updated_at"]
                ))
        return results

    def get_conversation(self, conversation_id: str, owner_id: str = "default_user") -> Optional[ConversationResponse]:
        rec = self._conversations.get(conversation_id)
        if not rec or rec["owner_id"] != owner_id:
            return None
        msg_count = len(self._messages.get(conversation_id, []))
        return ConversationResponse(
            conversation_id=conversation_id,
            title=rec["title"],
            knowledge_item_id=rec["knowledge_item_id"],
            collection_id=rec["collection_id"],
            owner_id=rec["owner_id"],
            message_count=msg_count,
            created_at=rec["created_at"],
            updated_at=rec["updated_at"]
        )

    def delete_conversation(self, conversation_id: str, owner_id: str = "default_user") -> bool:
        """Deletes conversation session & chat history. Does NOT delete library items or artifacts."""
        rec = self._conversations.get(conversation_id)
        if not rec or rec["owner_id"] != owner_id:
            return False

        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
        if conversation_id in self._messages:
            del self._messages[conversation_id]
        return True

    def list_messages(self, conversation_id: str, owner_id: str = "default_user") -> List[ChatMessageResponse]:
        conv = self.get_conversation(conversation_id, owner_id=owner_id)
        if not conv:
            return []
        msg_recs = self._messages.get(conversation_id, [])
        return [ChatMessageResponse(**m) for m in msg_recs]

    def post_message(self, conversation_id: str, request: PostMessageRequest) -> ChatMessageResponse:
        owner_id = request.owner_id or "default_user"
        conv = self._conversations.get(conversation_id)
        if not conv or conv["owner_id"] != owner_id:
            raise ValueError(f"Conversation '{conversation_id}' not found or access denied.")

        now = datetime.now(timezone.utc)
        user_msg_id = f"msg_{uuid.uuid4().hex[:10]}"
        
        user_msg_record = {
            "message_id": user_msg_id,
            "conversation_id": conversation_id,
            "role": "user",
            "content": request.content.strip(),
            "sources": [],
            "created_at": now
        }
        self._messages[conversation_id].append(user_msg_record)

        # Build Grounded Context via M5 Retrieval / Library Snapshot
        context_text, citations = self.context_builder.build_context(
            query=request.content,
            owner_id=owner_id,
            knowledge_item_id=conv.get("knowledge_item_id"),
            collection_id=conv.get("collection_id")
        )

        # Retrieve recent message history for follow-up question context
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in self._messages[conversation_id][-5:]
        ]

        # Call Grounded Gemini Provider via provider_manager
        assistant_content = provider_manager.answer_grounded_chat(
            user_question=request.content,
            retrieved_context_text=context_text,
            conversation_history=history
        )

        assist_msg_id = f"msg_{uuid.uuid4().hex[:10]}"
        assist_msg_record = {
            "message_id": assist_msg_id,
            "conversation_id": conversation_id,
            "role": "assistant",
            "content": assistant_content,
            "sources": [c.model_dump() for c in citations],
            "created_at": datetime.now(timezone.utc)
        }
        self._messages[conversation_id].append(assist_msg_record)
        conv["updated_at"] = datetime.now(timezone.utc)

        return ChatMessageResponse(
            message_id=assist_msg_id,
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
            sources=citations,
            created_at=assist_msg_record["created_at"]
        )


# Global singleton instance for conversation service
conversation_service = ConversationService()
