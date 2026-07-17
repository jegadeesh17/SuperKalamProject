"""
Orchestrator — Chains agents together in an agentic pipeline.
Retrieval → Evaluation → Feedback (for evaluate mode)
Retrieval → Translation (for model-answer mode)
"""

import json
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from agents.retrieval import retrieve
from agents.evaluator import evaluate
from agents.feedback import generate_feedback, translate_model_answer
from app.database import Attempt, Rubric


async def run_evaluate_pipeline(
    question_text: str,
    answer_text: str,
    language: str,
    db: Session,
    time_taken_seconds: int = None,
) -> dict:
    """
    Full evaluate pipeline: Retrieval → Evaluator → Feedback → Persist

    Returns the complete evaluation result dict.
    """
    # ── Step 1: Retrieval Agent ─────────────────────────────────
    retrieval_result = retrieve(question_text)

    if "error" in retrieval_result:
        pyq_id = "unknown"
        topic_id = "general"
        matched_question = question_text
        model_answer = "No official model answer available. Evaluate based on general UPSC knowledge."
        word_limit = 250
        year = None
    else:
        pyq_id = retrieval_result["pyq_id"]
        topic_id = retrieval_result["topic_id"]
        matched_question = retrieval_result["question_text"]
        model_answer = retrieval_result["model_answer"]
        word_limit = retrieval_result["word_limit"]
        year = retrieval_result["year"]

    # ── Step 2: Get rubric for this topic ───────────────────────
    rubric = db.query(Rubric).filter(Rubric.topic_id == topic_id).first()
    if rubric:
        rubric_criteria = json.loads(rubric.criteria_json)
    else:
        # Fallback to default rubric
        from app.config import settings
        rubric_criteria = [
            {"name": k, "weight": v, "description": f"Score for {k}"}
            for k, v in settings.DEFAULT_RUBRIC_WEIGHTS.items()
        ]

    # ── Step 3: Evaluator Agent ─────────────────────────────────
    evaluation = await evaluate(
        submitted_answer=answer_text,
        question_text=matched_question,
        model_answer=model_answer,
        rubric_criteria=rubric_criteria,
        word_limit=word_limit,
        time_taken_seconds=time_taken_seconds,
    )

    scores = evaluation["scores"]
    overall_score = evaluation["overall_score"]
    evaluator_notes = evaluation["notes"]

    # ── Step 4: Feedback Agent ──────────────────────────────────
    feedback = await generate_feedback(
        scores_json=scores,
        evaluator_notes=evaluator_notes,
        question_text=matched_question,
        language=language,
    )

    # ── Step 5: Persist to SQLite ───────────────────────────────
    attempt_id = str(uuid.uuid4())

    # Get topic title for response
    from app.database import Topic
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    topic_display = f"{topic.paper} — {topic.title}" if topic else topic_id

    attempt = Attempt(
        id=attempt_id,
        topic_id=topic_id,
        pyq_id=pyq_id,
        submitted_answer=answer_text,
        language=language,
        scores_json=json.dumps(scores),
        overall_score=overall_score,
        feedback_text=feedback,
        time_taken_seconds=time_taken_seconds,
        created_at=datetime.utcnow(),
    )
    db.add(attempt)
    db.commit()

    return {
        "attempt_id": attempt_id,
        "matched_question": matched_question,
        "topic": topic_display,
        "year": year,
        "scores": scores,
        "overall_score": overall_score,
        "feedback": feedback,
        "language": language,
        "time_taken_seconds": time_taken_seconds,
    }


async def run_model_answer_pipeline(
    question_text: str,
    language: str,
    db: Session,
) -> dict:
    """
    Model answer pipeline: Retrieval → Translation (if needed)

    Returns the model answer for the matched question.
    """
    # ── Step 1: Retrieval Agent ─────────────────────────────────
    retrieval_result = retrieve(question_text)

    if "error" in retrieval_result:
        raise ValueError(retrieval_result["error"])

    topic_id = retrieval_result["topic_id"]
    matched_question = retrieval_result["question_text"]
    model_answer = retrieval_result["model_answer"]
    key_points = retrieval_result["key_points"]
    word_limit = retrieval_result["word_limit"]
    year = retrieval_result["year"]

    # ── Step 2: Translate if needed ─────────────────────────────
    localized_answer = await translate_model_answer(model_answer, language)

    # ── Step 3: Get rubric for context ──────────────────────────
    rubric = db.query(Rubric).filter(Rubric.topic_id == topic_id).first()
    rubric_criteria = json.loads(rubric.criteria_json) if rubric else []

    # Get topic title
    from app.database import Topic
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    topic_display = f"{topic.paper} — {topic.title}" if topic else topic_id

    return {
        "matched_question": matched_question,
        "year": year,
        "topic": topic_display,
        "model_answer": localized_answer,
        "key_points": key_points,
        "word_limit": word_limit,
        "rubric_criteria": rubric_criteria,
    }
