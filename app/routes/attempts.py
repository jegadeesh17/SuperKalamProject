"""
Attempts Routes
GET /attempts/{attempt_id} — get a single past evaluation
GET /attempts — list past evaluations (optionally filtered by topic)
"""

import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db, Attempt
from app.models import AttemptResponse

router = APIRouter()


@router.get(
    "/attempts/{attempt_id}",
    response_model=AttemptResponse,
    summary="Get a single evaluation attempt",
    description="Returns the full details of a past evaluation attempt.",
)
async def get_attempt(attempt_id: str, db: Session = Depends(get_db)):
    attempt = db.query(Attempt).filter(Attempt.id == attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail=f"Attempt '{attempt_id}' not found")

    return AttemptResponse(
        id=attempt.id,
        topic_id=attempt.topic_id,
        pyq_id=attempt.pyq_id,
        submitted_answer=attempt.submitted_answer,
        language=attempt.language,
        scores=json.loads(attempt.scores_json),
        overall_score=attempt.overall_score,
        feedback_text=attempt.feedback_text,
        created_at=attempt.created_at.isoformat() if attempt.created_at else "",
    )


@router.get(
    "/attempts",
    response_model=list[AttemptResponse],
    summary="List past evaluation attempts",
    description="Returns a list of past evaluation attempts, optionally filtered by topic. Most recent first.",
)
async def list_attempts(
    topic_id: str = Query(None, description="Filter by topic ID"),
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
    db: Session = Depends(get_db),
):
    query = db.query(Attempt).order_by(Attempt.created_at.desc())

    if topic_id:
        query = query.filter(Attempt.topic_id == topic_id)

    attempts = query.limit(limit).all()

    return [
        AttemptResponse(
            id=a.id,
            topic_id=a.topic_id,
            pyq_id=a.pyq_id,
            submitted_answer=a.submitted_answer,
            language=a.language,
            scores=json.loads(a.scores_json),
            overall_score=a.overall_score,
            feedback_text=a.feedback_text,
            created_at=a.created_at.isoformat() if a.created_at else "",
        )
        for a in attempts
    ]
