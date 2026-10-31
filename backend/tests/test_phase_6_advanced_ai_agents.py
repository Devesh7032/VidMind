import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import (
    AgentTaskStatus,
    AgentTaskType,
    AgentRole
)
from app.services.agent_orchestrator_service import agent_orchestrator_service

client = TestClient(app)


def test_m1_ai_task_planning():
    """Requirement M1: AI Task Planning generates structured plans with dependencies."""
    owner_id = "user_p6_m1"
    plan = agent_orchestrator_service.create_task_plan("Prepare me for a DSA interview", owner_id=owner_id)

    assert plan.plan_id.startswith("plan_")
    assert plan.high_level_goal == "Prepare me for a DSA interview"
    assert len(plan.tasks) >= 4
    assert plan.tasks[0].agent_role == AgentRole.KNOWLEDGE_AGENT
    assert plan.tasks[1].dependencies == [plan.tasks[0].task_id]

    # API Endpoint Check
    res = client.post(
        "/api/agents/plans",
        json={"goal": "Help me master Kubernetes"},
        headers={"X-User-ID": owner_id}
    )
    assert res.status_code == 200
    data = res.json()
    assert "plan_id" in data
    assert len(data["tasks"]) >= 2


def test_m7_multi_agent_workflow_orchestration():
    """Requirement M7 & M9: Multi-agent orchestration executes specialized agents with budget controls."""
    owner_id = "user_p6_m7"
    headers = {"X-User-ID": owner_id}

    res = client.post(
        "/api/agents/workflows/execute",
        json={"goal": "Prepare me for a DSA interview", "autonomy_level": "ASSISTED"},
        headers=headers
    )
    assert res.status_code == 200
    exec_data = res.json()

    assert exec_data["overall_status"] == AgentTaskStatus.COMPLETED.value
    assert exec_data["completed_tasks"] >= 4
    assert "budget_usage" in exec_data
    assert exec_data["budget_usage"]["gemini_calls"] <= 10


def test_m8_agent_memory_and_explainability():
    """Requirement M8: Agent Memory & Execution History with action-level explainability."""
    owner_id = "user_p6_m8"
    headers = {"X-User-ID": owner_id}

    # Execute workflow to populate history
    client.post(
        "/api/agents/workflows/execute",
        json={"goal": "Analyze my DSA gaps"},
        headers=headers
    )

    # Fetch History
    res = client.get("/api/agents/history", headers=headers)
    assert res.status_code == 200
    hist = res.json()
    assert len(hist) >= 1
    assert hist[0]["execution_history"][0]["explanation"] is not None


def test_agent_loop_protection_and_budget_limits():
    """Requirement 41, 42, 67, 68: Loop protection caps task steps at MAX_AGENT_STEPS."""
    assert agent_orchestrator_service.MAX_AGENT_STEPS == 10
    assert agent_orchestrator_service.MAX_GEMINI_CALLS_PER_TASK == 10
