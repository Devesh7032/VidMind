import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from app.schemas import SearchResponse, SearchResultItem
from app.services.library_service import library_service


class SearchService:
    """
    VidMind Search & Retrieval Service.
    Provides deterministic full-text search, topic alias matching, multi-language filtering,
    relevance scoring, term highlighting, and collection-scoped retrieval.
    Never calls external AI LLMs for search query parsing.
    """

    def highlight_terms(self, text: str, query_terms: List[str]) -> str:
        """Wraps matched query terms in <mark> tags for visual emphasis."""
        if not text or not query_terms:
            return text or ""
        pattern = re.compile(r"(" + "|".join(re.escape(t) for t in query_terms if t) + r")", re.IGNORECASE)
        return pattern.sub(r"<mark>\1</mark>", text)

    def extract_snippet(self, content: str, query_terms: List[str], max_len: int = 160) -> str:
        """Extracts a contextual snippet centered around the first term match."""
        if not content or not query_terms:
            return (content or "")[:max_len]

        lowered_content = content.lower()
        match_idx = -1
        for term in query_terms:
            idx = lowered_content.find(term.lower())
            if idx != -1:
                match_idx = idx
                break

        if match_idx == -1:
            return content[:max_len]

        start = max(0, match_idx - 40)
        end = min(len(content), start + max_len)
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet

    def search(
        self,
        query: str,
        owner_id: str = "default_user",
        collection_id: Optional[str] = None,
        language: Optional[str] = None,
        topic: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> SearchResponse:
        """
        Executes deterministic search over user's saved library items.
        Applies title, topic, concept, code, and source metadata weighted scoring.
        """
        raw_query = (query or "").strip()
        if not raw_query:
            return SearchResponse(query="", total=0, page=page, page_size=page_size, results=[])

        query_terms = [t.lower() for t in raw_query.split() if len(t) > 1]
        if not query_terms:
            query_terms = [raw_query.lower()]

        # Retrieve items from library_service for owner_id
        items = library_service.list_knowledge_items(owner_id=owner_id, collection_id=collection_id)
        collections_map = {c.collection_id: c.name for c in library_service.list_collections(owner_id=owner_id)}

        scored_results: List[Tuple[float, Dict[str, Any], List[str], List[str], str]] = []

        for item in items:
            snapshot = item.knowledge_snapshot or {}
            canonical_nodes = snapshot.get("canonical_nodes") or snapshot.get("topic_nodes") or []
            
            # Collect topics & languages present in item
            item_topics: List[str] = []
            item_languages: List[str] = []
            all_text_blobs: List[str] = []

            for node in canonical_nodes:
                if isinstance(node, dict):
                    t_title = node.get("topic_title", "")
                    c_summary = node.get("concept_summary", "")
                    if t_title:
                        item_topics.append(t_title)
                    if c_summary:
                        all_text_blobs.append(c_summary)
                    
                    code_snippets = node.get("code_snippets") or []
                    for cs in code_snippets:
                        if isinstance(cs, dict):
                            lang = cs.get("language")
                            code_txt = cs.get("code_content", "")
                            if lang:
                                item_languages.append(lang.lower())
                            if code_txt:
                                all_text_blobs.append(code_txt)

            # Apply Language Filter if specified
            if language:
                req_lang = language.lower().strip()
                if not any(req_lang in l.lower() for l in item_languages):
                    continue

            # Apply Topic Filter if specified
            if topic:
                req_topic = topic.lower().strip()
                if not any(req_topic in t.lower() for t in item_topics):
                    continue

            # Calculate Relevance Score
            title_lower = item.title.lower()
            desc_lower = (item.description or "").lower()
            source_lower = item.source_url.lower()
            coll_name = collections_map.get(item.collection_id, "Collection")
            coll_lower = coll_name.lower()

            score = 0.0
            matched_topics_found: List[str] = []
            matched_langs_found: List[str] = []

            # 1. Title Matching (Weight 1.00 / 0.90)
            if raw_query.lower() in title_lower:
                score += 1.00 if raw_query.lower() == title_lower else 0.90
            elif any(t in title_lower for t in query_terms):
                score += 0.70

            # 2. Topic Title / Alias Matching (Weight 0.85)
            for top_title in item_topics:
                top_low = top_title.lower()
                if any(t in top_low for t in query_terms) or raw_query.lower() in top_low:
                    score += 0.85
                    if top_title not in matched_topics_found:
                        matched_topics_found.append(top_title)

            # 3. Concept / Content Matching (Weight 0.75)
            full_content_str = " ".join(all_text_blobs)
            if any(t in full_content_str.lower() for t in query_terms):
                score += 0.75

            # 4. Code & Language Matching (Weight 0.65)
            for lang_name in item_languages:
                if any(t in lang_name.lower() for t in query_terms):
                    score += 0.65
                    if lang_name not in matched_langs_found:
                        matched_langs_found.append(lang_name)

            # 5. Source / Collection Metadata Matching (Weight 0.50)
            if any(t in source_lower or t in coll_lower or t in desc_lower for t in query_terms):
                score += 0.50

            if score > 0.0:
                raw_snippet = self.extract_snippet(full_content_str or item.description or item.title, query_terms)
                scored_results.append((score, item.model_dump(), matched_topics_found, matched_langs_found, raw_snippet))

        # Sort by relevance score DESC, then updated_at DESC
        scored_results.sort(key=lambda x: (x[0], x[1].get("updated_at")), reverse=True)

        total_matches = len(scored_results)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_slice = scored_results[start_idx:end_idx]

        final_items: List[SearchResultItem] = []
        for score_val, item_dict, m_topics, m_langs, raw_snip in page_slice:
            c_name = collections_map.get(item_dict["collection_id"], "Collection")
            h_title = self.highlight_terms(item_dict["title"], query_terms)
            h_snippet = self.highlight_terms(raw_snip, query_terms)

            final_items.append(SearchResultItem(
                knowledge_item_id=item_dict["item_id"],
                title=item_dict["title"],
                collection_id=item_dict["collection_id"],
                collection_name=c_name,
                is_playlist=item_dict.get("is_playlist", False),
                matched_topics=m_topics,
                matched_languages=m_langs,
                snippet=raw_snip,
                highlighted_title=h_title,
                highlighted_snippet=h_snippet,
                score=round(score_val, 2),
                updated_at=item_dict["updated_at"]
            ))

        has_next = end_idx < total_matches

        return SearchResponse(
            query=raw_query,
            total=total_matches,
            page=page,
            page_size=page_size,
            has_next=has_next,
            results=final_items
        )


# Global singleton instance for search service
search_service = SearchService()
