"""
Topics & Questions Routes
GET /topics — list available topics
GET /topics/{topic_id}/questions — list questions for a topic
GET /questions/{question_id} — get full question details
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db, Topic, PYQ
from app.models import TopicResponse, QuestionResponse, QuestionDetailResponse

router = APIRouter()


@router.get(
    "/topics",
    response_model=list[TopicResponse],
    summary="List all available topics",
    description="Returns the list of UPSC GS topics with question counts.",
)
async def list_topics(db: Session = Depends(get_db)):
    topics = db.query(Topic).all()
    result = []
    for t in topics:
        q_count = db.query(PYQ).filter(PYQ.topic_id == t.id).count()
        result.append(TopicResponse(
            id=t.id,
            paper=t.paper,
            title=t.title,
            syllabus_note=t.syllabus_note or "",
            question_count=q_count,
        ))
    return result


@router.get(
    "/topics/{topic_id}/questions",
    response_model=list[QuestionResponse],
    summary="List questions for a topic",
    description="Returns all PYQs for the specified topic.",
)
async def list_questions(topic_id: str, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail=f"Topic '{topic_id}' not found")

    pyqs = db.query(PYQ).filter(PYQ.topic_id == topic_id).order_by(PYQ.year.desc()).all()
    return [
        QuestionResponse(
            id=p.id,
            topic_id=p.topic_id,
            question_text=p.question_text,
            year=p.year,
            word_limit=p.word_limit,
            difficulty=p.difficulty,
        )
        for p in pyqs
    ]


@router.get(
    "/questions/{question_id}",
    response_model=QuestionDetailResponse,
    summary="Get full question details",
    description="Returns a specific question with model answer and key points.",
)
async def get_question(question_id: str, db: Session = Depends(get_db)):
    pyq = db.query(PYQ).filter(PYQ.id == question_id).first()
    if not pyq:
        raise HTTPException(status_code=404, detail=f"Question '{question_id}' not found")

    key_points = json.loads(pyq.key_points) if pyq.key_points else []

    return QuestionDetailResponse(
        id=pyq.id,
        topic_id=pyq.topic_id,
        question_text=pyq.question_text,
        year=pyq.year,
        word_limit=pyq.word_limit,
        difficulty=pyq.difficulty,
        model_answer=pyq.model_answer,
        key_points=key_points,
    )
