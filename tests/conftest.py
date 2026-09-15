"""
Pytest configuration and fixtures for SuperKalam.
Mocks external OpenRouter LLM HTTP requests for fast, deterministic, zero-cost test runs.
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app
from app.database import create_tables, SessionLocal, get_db, Topic, PYQ, Rubric, Base, engine


@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    """Ensure database tables exist and insert test fixture if empty."""
    create_tables()
    db = SessionLocal()
    try:
        topic = db.query(Topic).filter_by(id="test-gs2-federalism").first()
        if not topic:
            topic = Topic(
                id="test-gs2-federalism",
                paper="GS Paper II",
                title="Federalism Test Topic",
                syllabus_note="Test syllabus note"
            )
            db.add(topic)
            db.commit()

            pyq = PYQ(
                id="test-pyq-1",
                topic_id="test-gs2-federalism",
                question_text="Discuss the challenges to cooperative federalism in India with suitable examples.",
                year=2021,
                model_answer="Cooperative federalism requires active consultation between Centre and States...",
                key_points='["GST Council", "Inter-State Council", "Finance Commission"]',
                word_limit=250,
                difficulty="moderate"
            )
            db.add(pyq)

            rubric = Rubric(
                topic_id="test-gs2-federalism",
                criteria_json="""[
                    {"name": "Content & Accuracy", "weight": 0.40, "description": "Accurate coverage of constitutional provisions."},
                    {"name": "Structure & Flow", "weight": 0.25, "description": "Clear introduction, body, and balanced conclusion."},
                    {"name": "Examples & Case Studies", "weight": 0.20, "description": "Concrete examples like GST, pandemic management."},
                    {"name": "Word Count & Time", "weight": 0.15, "description": "Adherence to word limit."}
                ]"""
            )
            db.add(rubric)
            db.commit()
    finally:
        db.close()


@pytest.fixture
def client():
    """FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_evaluator_response():
    """Standard valid evaluator agent output dictionary."""
    return {
        "scores": {
            "Content & Accuracy": 8,
            "Structure & Flow": 7,
            "Examples & Case Studies": 8,
            "Word Count & Time": 9
        },
        "overall_score": 7.9,
        "notes": "Solid understanding of federal mechanisms. Good citations of GST Council. Conclusion could be more forward-looking."
    }


@pytest.fixture
def mock_feedback_response():
    """Standard mentor feedback agent output string."""
    return (
        "Great attempt! You scored 7.9/10. Solid coverage of constitutional federal provisions "
        "and active consultative councils. To improve further, incorporate specific committee "
        "recommendations such as the Punchhi Commission report in your analytical body."
    )
