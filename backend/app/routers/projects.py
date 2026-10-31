from typing import List, Dict, Any
from fastapi import APIRouter, Header, HTTPException, status
from app.schemas import (
    ProjectCreateRequest,
    ProjectResponse,
    IngestionResultResponse,
    MultimodalFusionResponse,
    IntermediateKnowledgeRepresentation,
    ProjectArtifactsListResponse,
    PlaylistMetadataResponse,
    UnifiedPlaylistKnowledgeGraph
)
from app.services.project_service import project_service
from app.services.ingestion_service import ingestion_service
from app.services.multimodal_fusion_service import multimodal_fusion_service
from app.services.knowledge_reasoning_service import knowledge_reasoning_service
from app.services.artifact_service import artifact_service

router = APIRouter(prefix="/api/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreateRequest,
    x_user_id: str = Header(default="default_user")
):
    """
    Create a new VidMind project from a single video or playlist URL and user prompt.
    Validates source URL syntax, SSRF safety, and prompt length before registering project.
    """
    try:
        project = project_service.create_project(request, owner_id=x_user_id)
        return project
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register project: {str(e)}"
        )


@router.get("", response_model=List[ProjectResponse])
async def list_projects(x_user_id: str = Header(default="default_user")):
    """Retrieve all registered projects owned by requesting user."""
    return project_service.list_projects(owner_id=x_user_id)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, x_user_id: str = Header(default="default_user")):
    """Retrieve project details by unique project_id with IDOR ownership validation."""
    project = project_service.get_project(project_id, owner_id=x_user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found or access denied."
        )
    return project


@router.get("/{project_id}/playlist", response_model=PlaylistMetadataResponse)
async def get_project_playlist_metadata(project_id: str, x_user_id: str = Header(default="default_user")):
    """Retrieve playlist metadata for owned project."""
    project = project_service.get_project(project_id, owner_id=x_user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found or access denied."
        )
    if not project.is_playlist or not project.playlist_metadata:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project '{project_id}' is not a playlist project."
        )
    return project.playlist_metadata


@router.get("/{project_id}/playlist/knowledge", response_model=UnifiedPlaylistKnowledgeGraph)
async def get_playlist_unified_knowledge(project_id: str, x_user_id: str = Header(default="default_user")):
    """Retrieve unified playlist knowledge graph for owned project."""
    project = project_service.get_project(project_id, owner_id=x_user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found or access denied."
        )
    
    graph = knowledge_reasoning_service.get_playlist_knowledge_graph(project_id)
    if not graph:
        try:
            graph = knowledge_reasoning_service.synthesize_playlist_knowledge_graph(project_id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unified knowledge graph for project '{project_id}' not yet available or failed: {str(e)}"
            )
    return graph


@router.get("/{project_id}/ingestion", response_model=IngestionResultResponse)
async def get_project_ingestion_result(project_id: str, x_user_id: str = Header(default="default_user")):
    """Retrieve ingestion result for owned project."""
    project = project_service.get_project(project_id, owner_id=x_user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found or access denied."
        )

    ingestion_result = ingestion_service.get_ingestion_result(project_id)
    if not ingestion_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingestion result for project '{project_id}' not yet available or in progress."
        )
    return ingestion_result


@router.get("/{project_id}/evidence", response_model=MultimodalFusionResponse)
async def get_project_fused_evidence(project_id: str, x_user_id: str = Header(default="default_user")):
    """Retrieve multimodal fused evidence for owned project."""
    project = project_service.get_project(project_id, owner_id=x_user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found or access denied."
        )

    fusion_result = multimodal_fusion_service.get_fusion_result(project_id)
    if not fusion_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fused evidence for project '{project_id}' not yet available or in progress."
        )
    return fusion_result


@router.get("/{project_id}/knowledge", response_model=IntermediateKnowledgeRepresentation)
async def get_project_knowledge_representation(project_id: str, x_user_id: str = Header(default="default_user")):
    """Retrieve Intermediate Knowledge Representation for owned project."""
    project = project_service.get_project(project_id, owner_id=x_user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found or access denied."
        )

    ikr = knowledge_reasoning_service.get_knowledge_representation(project_id)
    if not ikr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge representation for project '{project_id}' not yet available or in progress."
        )
    return ikr


@router.get("/{project_id}/artifacts", response_model=ProjectArtifactsListResponse)
async def list_project_artifacts(project_id: str, x_user_id: str = Header(default="default_user")):
    """Retrieve list of generated artifacts for owned project."""
    project = project_service.get_project(project_id, owner_id=x_user_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found or access denied."
        )

    try:
        res = artifact_service.generate_project_artifacts(project_id)
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate or list artifacts: {str(e)}"
        )
