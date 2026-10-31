from fastapi import APIRouter, HTTPException, status
from app.schemas import IntentPlanRequest, ExtractionPlan
from app.services.ai.intent_engine import intent_engine

router = APIRouter(prefix="/api/intents", tags=["Intent Engine"])


@router.post("/plan", response_model=ExtractionPlan, status_code=status.HTTP_200_OK)
async def generate_intent_plan(request: IntentPlanRequest):
    """
    Translates a freeform natural-language prompt into a schema-validated ExtractionPlan.
    """
    try:
        plan = intent_engine.create_extraction_plan(request.prompt)
        return plan
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to generate intent plan: {str(e)}"
        )
