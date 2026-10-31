import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from app.schemas import (
    CollectionCreateRequest,
    CollectionUpdateRequest,
    CollectionResponse,
    SaveToLibraryResponse,
    KnowledgeItemResponse,
    ProjectStatus
)
from app.services.project_service import project_service
from app.services.knowledge_reasoning_service import knowledge_reasoning_service
from app.services.artifact_service import artifact_service


class LibraryService:
    """
    VidMind Personal Knowledge Library Service.
    Manages persistent collections, knowledge item saving, duplicate protection,
    ownership isolation, and provenance-preserving item retrieval.
    """

    def __init__(self):
        # In-memory stores (backed by SQLite/PostgreSQL schema in production)
        # collection_id -> collection dict
        self._collections: Dict[str, Dict[str, Any]] = {}
        # item_id -> item dict
        self._items: Dict[str, Dict[str, Any]] = {}

        # Pre-seed default collections if empty
        self._initialize_default_collections()

    def _initialize_default_collections(self):
        now = datetime.now(timezone.utc)
        defaults = [
            ("col_dsa", "DSA", "Data Structures & Algorithms"),
            ("col_aiml", "AI / ML", "Artificial Intelligence & Machine Learning"),
            ("col_web", "Web Development", "Frontend, Backend & Web Architecture")
        ]
        for c_id, name, desc in defaults:
            if c_id not in self._collections:
                self._collections[c_id] = {
                    "collection_id": c_id,
                    "name": name,
                    "description": desc,
                    "owner_id": "default_user",
                    "created_at": now,
                    "updated_at": now
                }

    # --- COLLECTION MANAGEMENT APIs ---

    def create_collection(self, request: CollectionCreateRequest) -> CollectionResponse:
        owner_id = request.owner_id or "default_user"
        c_id = f"col_{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc)

        record = {
            "collection_id": c_id,
            "name": request.name.strip(),
            "description": (request.description or "").strip(),
            "owner_id": owner_id,
            "created_at": now,
            "updated_at": now
        }
        self._collections[c_id] = record
        return self._build_collection_response(record)

    def list_collections(self, owner_id: str = "default_user") -> List[CollectionResponse]:
        results = []
        for rec in self._collections.values():
            if rec["owner_id"] == owner_id:
                results.append(self._build_collection_response(rec))
        return results

    def get_collection(self, collection_id: str, owner_id: str = "default_user") -> Optional[CollectionResponse]:
        rec = self._collections.get(collection_id)
        if not rec or rec["owner_id"] != owner_id:
            return None
        return self._build_collection_response(rec)

    def update_collection(self, collection_id: str, request: CollectionUpdateRequest, owner_id: str = "default_user") -> Optional[CollectionResponse]:
        rec = self._collections.get(collection_id)
        if not rec or rec["owner_id"] != owner_id:
            return None

        if request.name is not None and request.name.strip():
            rec["name"] = request.name.strip()
        if request.description is not None:
            rec["description"] = request.description.strip()

        rec["updated_at"] = datetime.now(timezone.utc)
        return self._build_collection_response(rec)

    def delete_collection(self, collection_id: str, owner_id: str = "default_user") -> bool:
        """
        Safely deletes a collection and library item associations for owner_id.
        Does NOT delete original project data or disk artifacts.
        """
        rec = self._collections.get(collection_id)
        if not rec or rec["owner_id"] != owner_id:
            return False

        # Remove item associations belonging to collection
        items_to_del = [item_id for item_id, item in self._items.items() if item["collection_id"] == collection_id and item["owner_id"] == owner_id]
        for item_id in items_to_del:
            del self._items[item_id]

        del self._collections[collection_id]
        return True

    def _build_collection_response(self, rec: Dict[str, Any]) -> CollectionResponse:
        c_id = rec["collection_id"]
        o_id = rec["owner_id"]
        count = sum(1 for item in self._items.values() if item["collection_id"] == c_id and item["owner_id"] == o_id)
        return CollectionResponse(
            collection_id=c_id,
            name=rec["name"],
            description=rec.get("description", ""),
            owner_id=o_id,
            item_count=count,
            created_at=rec["created_at"],
            updated_at=rec["updated_at"]
        )

    # --- PROJECT -> LIBRARY SAVE & ITEM APIs ---

    def save_project_to_library(self, project_id: str, collection_id: str, owner_id: str = "default_user") -> SaveToLibraryResponse:
        project = project_service.get_project(project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found.")

        # Validation: Must be completed
        valid_states = [ProjectStatus.COMPLETED, ProjectStatus.PARTIALLY_FAILED]
        if project.status not in valid_states:
            raise ValueError(f"Cannot save project to library. Current project status is '{project.status.value}'. Project must be completed.")

        collection = self.get_collection(collection_id, owner_id=owner_id)
        if not collection:
            raise ValueError(f"Collection '{collection_id}' not found or access denied.")

        # Idempotency / Duplicate Save Protection: Check if project already saved in collection
        for existing_item in self._items.values():
            if (
                existing_item["project_id"] == project_id
                and existing_item["collection_id"] == collection_id
                and existing_item["owner_id"] == owner_id
            ):
                return SaveToLibraryResponse(
                    knowledge_item_id=existing_item["item_id"],
                    collection_id=collection_id,
                    project_id=project_id,
                    status="already_saved",
                    message="Project is already saved in this collection."
                )

        # Retrieve Knowledge Snapshot (Unified Graph or IKR)
        snapshot_dict: Dict[str, Any] = {}
        if project.is_playlist:
            graph = knowledge_reasoning_service.get_playlist_knowledge_graph(project_id)
            if graph:
                snapshot_dict = graph.model_dump()
        else:
            ikr = knowledge_reasoning_service.get_knowledge_representation(project_id)
            if ikr:
                snapshot_dict = ikr.model_dump()

        # Retrieve Artifact References
        artifact_refs: List[Dict[str, Any]] = []
        try:
            art_list = artifact_service.generate_project_artifacts(project_id)
            if art_list and art_list.artifacts:
                artifact_refs = [a.model_dump() for a in art_list.artifacts]
        except Exception:
            pass

        title = f"{project.user_prompt[:50]}..." if len(project.user_prompt) > 50 else project.user_prompt
        item_id = f"item_{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc)

        item_record = {
            "item_id": item_id,
            "collection_id": collection_id,
            "project_id": project_id,
            "title": title,
            "description": f"Knowledge pack generated for {project.source_url}",
            "owner_id": owner_id,
            "is_playlist": bool(project.is_playlist),
            "source_url": project.source_url,
            "knowledge_snapshot": snapshot_dict,
            "artifact_references": artifact_refs,
            "created_at": now,
            "updated_at": now
        }

        self._items[item_id] = item_record

        return SaveToLibraryResponse(
            knowledge_item_id=item_id,
            collection_id=collection_id,
            project_id=project_id,
            status="saved",
            message="Project successfully saved to personal knowledge library."
        )

    def list_knowledge_items(self, owner_id: str = "default_user", collection_id: Optional[str] = None) -> List[KnowledgeItemResponse]:
        results = []
        for rec in self._items.values():
            if rec["owner_id"] == owner_id:
                if collection_id is None or rec["collection_id"] == collection_id:
                    results.append(KnowledgeItemResponse(**rec))
        return results

    def get_knowledge_item(self, item_id: str, owner_id: str = "default_user") -> Optional[KnowledgeItemResponse]:
        rec = self._items.get(item_id)
        if not rec or rec["owner_id"] != owner_id:
            return None
        return KnowledgeItemResponse(**rec)


# Global singleton instance for library service
library_service = LibraryService()
