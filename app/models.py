"""
SuperKalam Pydantic Schemas
Request/response models for API validation.
"""

from typing import Optional
from pydantic import BaseModel, Field


# ─── Request Schemas ──────────────────────────────────────────

class EvaluateRequest(BaseModel):
    """POST /evaluate — student submits question + answer for evaluation."""
    question_text: str = Field(
        ...,
        min_length=10,
        description="The UPSC Mains question the student is answering.",
        json_schema_extra={"example": "Discuss the role of cooperative federalism in India's governance."},
    )
    answer_text: str = Field(
        ...,
        min_length=20,
        description="The student's written answer (typically 150-300 words).",
        json_schema_extra={"example": "India's federal structure is unique in its design..."},
    )
    language: str = Field(
        default="en",
        pattern="^(en|hi|ta)$",
        description="Language for feedback: 'en' (English), 'hi' (Hindi), 'ta' (Tamil).",
    )
    time_taken_seconds: Optional[int] = Field(
        default=None,
        description="Time taken by the student to answer the question, in seconds.",
    )


class ModelAnswerRequest(BaseModel):
    """POST /model-answer — student submits a question to see the model answer."""
    question_text: str = Field(
        ...,
        min_length=10,
        description="The UPSC Mains question to get a model answer for.",
        json_schema_extra={"example": "What are the challenges to India's federal structure?"},
    )
    language: str = Field(
        default="en",
        pattern="^(en|hi|ta)$",
        description="Language for the model answer: 'en', 'hi', or 'ta'.",
    )


# ─── Response Schemas ─────────────────────────────────────────

class EvaluateResponse(BaseModel):
    """Response from POST /evaluate."""
    attempt_id: str
    matched_question: str
    topic: str
    year: Optional[int] = None
    scores: dict = Field(
        ...,
        json_schema_extra={"example": {"coverage": 7, "structure": 6, "examples": 5, "word_limit_adherence": 8}},
    )
    overall_score: float
    feedback: str
    language: str


class ModelAnswerResponse(BaseModel):
    """Response from POST /model-answer."""
    matched_question: str
    year: Optional[int] = None
    topic: str
    model_answer: str
    key_points: list[str]
    word_limit: int
    rubric_criteria: list[dict]


class TopicResponse(BaseModel):
    """A topic in the GET /topics response."""
    id: str
    paper: str
    title: str
    syllabus_note: str
    question_count: int


class QuestionResponse(BaseModel):
    """A question in the GET /topics/{id}/questions response."""
    id: str
    topic_id: str
    question_text: str
    year: Optional[int] = None
    word_limit: int
    difficulty: str


class QuestionDetailResponse(QuestionResponse):
    """Full question detail including model answer."""
    model_answer: str
    key_points: list[str]


class AttemptResponse(BaseModel):
    """A single attempt in GET /attempts responses."""
    id: str
    topic_id: str
    pyq_id: str
    submitted_answer: str
    language: str
    scores: dict
    overall_score: float
    feedback_text: str
    time_taken_seconds: Optional[int]
    created_at: str
