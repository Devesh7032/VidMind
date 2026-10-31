from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Header, HTTPException, status, Query
from app.schemas import (
    KnowledgeProfileResponse,
    KnowledgeGapResponse,
    LearningPathResponse,
    TutorRequest,
    TutorResponse,
    RevisionItemResponse,
    RecommendationItem,
    PersonalWorkspaceDashboardResponse
)
from app.services.personal_intelligence_service import personal_intelligence_service

router = APIRouter(prefix="/api/intelligence", tags=["Phase 5 — Intelligence & Personalization"])


@router.get("/profile", response_model=KnowledgeProfileResponse)
async def get_knowledge_profile(x_user_id: str = Header(default="default_user")):
    """M1: Retrieve structured Personal Knowledge Profile & Concept Mastery map."""
    return personal_intelligence_service.get_knowledge_profile(owner_id=x_user_id)


@router.get("/gaps", response_model=List[KnowledgeGapResponse])
async def detect_knowledge_gaps(x_user_id: str = Header(default="default_user")):
    """M3: Detect missing prerequisite concepts and knowledge gaps."""
    return personal_intelligence_service.detect_knowledge_gaps(owner_id=x_user_id)


@router.post("/learning-paths", response_model=LearningPathResponse)
async def generate_learning_path(
    goal: str = Query("DSA Interview Preparation", description="Target study goal"),
    x_user_id: str = Header(default="default_user")
):
    """M4: Generate personalized sequential study steps based on current mastery and gaps."""
    personal_intelligence_service.set_user_goal(goal, owner_id=x_user_id)
    return personal_intelligence_service.generate_learning_path(target_goal=goal, owner_id=x_user_id)


@router.post("/tutor", response_model=TutorResponse)
async def interact_with_tutor(
    request: TutorRequest,
    x_user_id: str = Header(default="default_user")
):
    """M5: Interact with Grounded Adaptive AI Tutor (TEACH, QUIZ, EXPLAIN, PRACTICE)."""
    try:
        return personal_intelligence_service.interact_with_tutor(request, owner_id=x_user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tutor interaction failed: {str(e)}"
        )


@router.get("/revisions", response_model=List[RevisionItemResponse])
async def get_revision_items(x_user_id: str = Header(default="default_user")):
    """M6: Fetch active recall flashcard questions and scheduled revision items."""
    return personal_intelligence_service.get_revision_items(owner_id=x_user_id)


@router.get("/recommendations", response_model=List[RecommendationItem])
async def get_recommendations(x_user_id: str = Header(default="default_user")):
    """M7: Retrieve grounded recommendations on what to learn or review next."""
    return personal_intelligence_service.get_recommendations(owner_id=x_user_id)


@router.get("/cross-source/compare")
async def compare_cross_sources(
    topic: str = Query("Dijkstra", description="Topic to compare across sources"),
    x_user_id: str = Header(default="default_user")
):
    """M8: Advanced cross-source comparison and conflict detection across videos and playlists."""
    return personal_intelligence_service.compare_cross_sources(topic, owner_id=x_user_id)


@router.get("/workspace", response_model=PersonalWorkspaceDashboardResponse)
async def get_workspace_dashboard(x_user_id: str = Header(default="default_user")):
    """M9: Retrieve Personal AI Workspace Dashboard aggregating profile, gaps, paths, revisions, and recommendations."""
    return personal_intelligence_service.get_personal_workspace_dashboard(owner_id=x_user_id)
