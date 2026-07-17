"""
Evaluate Route — POST /evaluate
Student submits question + answer → get scores + feedback
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EvaluateRequest, EvaluateResponse
from agents.orchestrator import run_evaluate_pipeline

router = APIRouter()


@router.post(
    "/evaluate",
    response_model=EvaluateResponse,
    summary="Evaluate a student's answer",
    description=(
        "Submit a UPSC Mains question and your written answer. "
        "The system auto-matches to the closest PYQ, scores your answer "
        "against the rubric, and returns mentor-style feedback in your chosen language."
    ),
)
async def evaluate_answer(
    request: EvaluateRequest,
    db: Session = Depends(get_db),
):
    try:
        result = await run_evaluate_pipeline(
            question_text=request.question_text,
            answer_text=request.answer_text,
            language=request.language,
            db=db,
        )
        return EvaluateResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"LLM evaluation failed: {str(e)}",
        )
