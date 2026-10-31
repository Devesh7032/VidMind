import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, List
from app.schemas import ProjectCreateRequest, ProjectResponse, ProjectStatus, ExtractionPlan
from app.services.ai.intent_engine import intent_engine
from app.services.playlist_service import playlist_service


class ProjectService:
    def __init__(self):
        # In-memory store (backed by database schema in production)
        self._projects: Dict[str, Dict] = {}

    def create_project(self, request: ProjectCreateRequest, owner_id: str = "default_user") -> ProjectResponse:
        project_id = f"proj_{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc)
        
        # Parse user prompt intent into structured ExtractionPlan
        plan: ExtractionPlan = intent_engine.create_extraction_plan(request.user_prompt)

        is_playlist = playlist_service.is_playlist_url(request.source_url)
        playlist_id = None
        playlist_metadata_dict = None

        if is_playlist:
            pl_meta = playlist_service.extract_playlist_metadata(request.source_url)
            playlist_id = pl_meta.playlist_id
            playlist_metadata_dict = pl_meta.model_dump()

        project_record = {
            "project_id": project_id,
            "source_url": request.source_url,
            "user_prompt": request.user_prompt,
            "status": ProjectStatus.PENDING,
            "owner_id": owner_id,
            "is_playlist": is_playlist,
            "playlist_id": playlist_id,
            "playlist_metadata": playlist_metadata_dict,
            "created_at": now,
            "updated_at": now,
            "extraction_plan": plan.model_dump(),
            "artifact_summary": None,
            "error_message": None
        }
        
        self._projects[project_id] = project_record
        return ProjectResponse(**project_record)

    def get_project(self, project_id: str, owner_id: Optional[str] = None) -> Optional[ProjectResponse]:
        record = self._projects.get(project_id)
        if not record:
            return None
        # Verify ownership if owner_id provided (IDOR Defense)
        if owner_id and record.get("owner_id", "default_user") != owner_id:
            return None
        return ProjectResponse(**record)

    def list_projects(self, owner_id: Optional[str] = None) -> List[ProjectResponse]:
        results = []
        for rec in self._projects.values():
            if owner_id and rec.get("owner_id", "default_user") != owner_id:
                continue
            results.append(ProjectResponse(**rec))
        return results

    def update_status(self, project_id: str, status: ProjectStatus, error_message: Optional[str] = None) -> Optional[ProjectResponse]:
        record = self._projects.get(project_id)
        if not record:
            return None
        record["status"] = status
        record["updated_at"] = datetime.now(timezone.utc)
        if error_message:
            record["error_message"] = error_message
        return ProjectResponse(**record)


# Global singleton instance for service layer access
project_service = ProjectService()
