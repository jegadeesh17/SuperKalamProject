"""
Model Answer Route — POST /model-answer
Student submits a question → get the model answer in chosen language
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ModelAnswerRequest, ModelAnswerResponse
from agents.orchestrator import run_model_answer_pipeline

router = APIRouter()


@router.post(
    "/model-answer",
    response_model=ModelAnswerResponse,
    summary="Get model answer for a question",
    description=(
        "Submit a UPSC Mains question to see the model answer. "
        "The system auto-matches to the closest PYQ and returns the "
        "model answer in your chosen language (English, Hindi, or Tamil)."
    ),
)
async def get_model_answer(
    request: ModelAnswerRequest,
    db: Session = Depends(get_db),
):
    try:
        result = await run_model_answer_pipeline(
            question_text=request.question_text,
            language=request.language,
            db=db,
        )
        return ModelAnswerResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Model answer retrieval failed: {str(e)}",
        )
