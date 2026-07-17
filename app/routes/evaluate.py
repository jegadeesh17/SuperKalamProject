"""
Evaluate Route — POST /evaluate
Student submits question + answer → get scores + feedback
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db, PYQ
from app.models import EvaluateRequest, EvaluateResponse
from agents.orchestrator import run_evaluate_pipeline
from sqlalchemy.sql.expression import func

router = APIRouter()

@router.get("/random-question")
async def get_random_question(db: Session = Depends(get_db)):
    """Fetch a random PYQ for the mock test."""
    question = db.query(PYQ).order_by(func.random()).first()
    if not question:
        raise HTTPException(status_code=404, detail="No questions found in database.")
    return {
        "question_text": question.question_text,
        "word_limit": question.word_limit,
        "year": question.year,
    }

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
            time_taken_seconds=request.time_taken_seconds,
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
