from typing import List
from fastapi import APIRouter, Header, HTTPException, status
from app.schemas import (
    AgentExecutionRequest,
    AgentExecutionResponse,
    AgentPlanResponse
)
from app.services.agent_orchestrator_service import agent_orchestrator_service

router = APIRouter(prefix="/api/agents", tags=["Phase 6 — AI Agents & Autonomous Workflows"])


@router.post("/plans", response_model=AgentPlanResponse)
async def create_agent_plan(
    request: AgentExecutionRequest,
    x_user_id: str = Header(default="default_user")
):
    """M1: Generate structured multi-step AI Task Plan with dependencies from high-level goal."""
    try:
        return agent_orchestrator_service.create_task_plan(
            goal=request.goal,
            owner_id=x_user_id,
            autonomy_level=request.autonomy_level or "ASSISTED"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to generate task plan: {str(e)}"
        )


@router.post("/workflows/execute", response_model=AgentExecutionResponse)
async def execute_agent_workflow(
    request: AgentExecutionRequest,
    x_user_id: str = Header(default="default_user")
):
    """M7 & M9: Orchestrate specialized AI agents to execute autonomous multi-step knowledge task."""
    try:
        return agent_orchestrator_service.execute_agent_workflow(
            goal=request.goal,
            owner_id=x_user_id,
            autonomy_level=request.autonomy_level or "ASSISTED"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent workflow execution failed: {str(e)}"
        )


@router.get("/history", response_model=List[AgentExecutionResponse])
async def get_agent_history(x_user_id: str = Header(default="default_user")):
    """M8: Retrieve agent memory and explainable execution history for authorized user."""
    return agent_orchestrator_service.get_execution_history(owner_id=x_user_id)
