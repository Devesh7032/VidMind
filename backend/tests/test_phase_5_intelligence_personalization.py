import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import (
    MasteryLevel,
    TutorMode,
    KnowledgeGapType,
    RecommendationType
)
from app.services.personal_intelligence_service import personal_intelligence_service
from app.services.library_service import library_service

client = TestClient(app)


def test_m1_personal_knowledge_profile():
    """Requirement M1: Personal Knowledge Profile & Concept Mastery Map."""
    owner_id = "user_p5_m1"
    headers = {"X-User-ID": owner_id}

    profile = personal_intelligence_service.get_knowledge_profile(owner_id=owner_id)
    assert profile.owner_id == owner_id
    assert isinstance(profile.top_skills, list)

    # API Endpoint check
    res = client.get("/api/intelligence/profile", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["owner_id"] == owner_id


def test_m3_knowledge_gap_detection():
    """Requirement M3: Detect missing prerequisite concepts and knowledge gaps."""
    owner_id = "user_p5_m3"
    headers = {"X-User-ID": owner_id}

    gaps = personal_intelligence_service.detect_knowledge_gaps(owner_id=owner_id)
    assert isinstance(gaps, list)

    res = client.get("/api/intelligence/gaps", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_m4_intelligent_learning_paths():
    """Requirement M4: Generate personalized sequential study steps based on goals and gaps."""
    owner_id = "user_p5_m4"
    headers = {"X-User-ID": owner_id}

    res = client.post(
        "/api/intelligence/learning-paths?goal=DSA%20Interview%20Prep",
        headers=headers
    )
    assert res.status_code == 200
    path_data = res.json()
    assert path_data["target_goal"] == "DSA Interview Prep"
    assert len(path_data["steps"]) >= 3


def test_m5_adaptive_ai_tutor():
    """Requirement M5: Grounded adaptive AI tutor supporting TEACH, QUIZ, EXPLAIN modes."""
    owner_id = "user_p5_m5"
    headers = {"X-User-ID": owner_id}

    res = client.post(
        "/api/intelligence/tutor",
        json={
            "mode": TutorMode.TEACH.value,
            "question": "Explain BFS algorithm step by step."
        },
        headers=headers
    )
    assert res.status_code == 200
    reply = res.json()
    assert reply["mode"] == TutorMode.TEACH.value
    assert len(reply["tutor_reply"]) > 10


def test_m6_smart_revision_and_recall():
    """Requirement M6: Smart Revision & Active Recall Flashcard items."""
    owner_id = "user_p5_m6"
    headers = {"X-User-ID": owner_id}

    res = client.get("/api/intelligence/revisions", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1
    assert "question" in items[0]


def test_m7_knowledge_recommendations():
    """Requirement M7: Knowledge Recommendations Engine grounded in gaps and recent topics."""
    owner_id = "user_p5_m7"
    headers = {"X-User-ID": owner_id}

    res = client.get("/api/intelligence/recommendations", headers=headers)
    assert res.status_code == 200
    recs = res.json()
    assert len(recs) >= 1
    assert "target_topic" in recs[0]


def test_m8_cross_source_comparison():
    """Requirement M8: Advanced Cross-Source Comparison & Conflict Detection."""
    owner_id = "user_p5_m8"
    headers = {"X-User-ID": owner_id}

    res = client.get("/api/intelligence/cross-source/compare?topic=Dijkstra", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["topic"] == "Dijkstra"
    assert "consensus_points" in data


def test_m9_personal_ai_workspace_dashboard():
    """Requirement M9: Personal AI Workspace Dashboard aggregating profile, gaps, learning path, revisions, and recs."""
    owner_id = "user_p5_m9"
    headers = {"X-User-ID": owner_id}

    res = client.get("/api/intelligence/workspace", headers=headers)
    assert res.status_code == 200
    dash = res.json()
    assert dash["owner_id"] == owner_id
    assert "knowledge_profile" in dash
    assert "recent_gaps" in dash
    assert "recommendations" in dash
