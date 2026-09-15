"""
Comprehensive Unit Tests for SuperKalam Agent Pipeline
Tests Evaluator, Feedback, Translation, and Orchestrator components with mocked LLM calls.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import httpx

from agents.evaluator import evaluate, _validate_evaluation
from agents.feedback import generate_feedback, translate_model_answer
from agents.orchestrator import run_evaluate_pipeline
from app.config import settings, Settings
from app.database import SessionLocal, Topic, Rubric, Attempt


@pytest.fixture
def standard_rubric():
    return [
        {"name": "Content & Accuracy", "weight": 0.40, "description": "Subject accuracy"},
        {"name": "Structure & Flow", "weight": 0.30, "description": "Logical flow"},
        {"name": "Examples & Case Studies", "weight": 0.30, "description": "Case studies"}
    ]


# ── Evaluator Agent Tests ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_evaluator_valid_json_response(standard_rubric):
    mock_payload = {
        "scores": {
            "Content & Accuracy": 8,
            "Structure & Flow": 7,
            "Examples & Case Studies": 9
        },
        "overall_score": 8.0,
        "notes": "Excellent factual precision and relevant case studies cited."
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(mock_payload)}}]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await evaluate(
            submitted_answer="Cooperative federalism requires active consultation...",
            question_text="Discuss federalism",
            model_answer="Model answer text",
            rubric_criteria=standard_rubric,
            word_limit=250,
        )

        assert result["overall_score"] == 8.0
        assert result["scores"]["Content & Accuracy"] == 8
        assert "precision" in result["notes"]


@pytest.mark.asyncio
async def test_evaluator_markdown_fence_stripping(standard_rubric):
    mock_payload = {
        "scores": {
            "Content & Accuracy": 7,
            "Structure & Flow": 8,
            "Examples & Case Studies": 7
        },
        "overall_score": 7.3,
        "notes": "Good flow, satisfactory examples."
    }
    fenced_content = f"```json\n{json.dumps(mock_payload)}\n```"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": fenced_content}}]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await evaluate(
            submitted_answer="A valid student answer...",
            question_text="Discuss federalism",
            model_answer="Model answer text",
            rubric_criteria=standard_rubric,
        )

        assert result["overall_score"] == 7.3
        assert result["scores"]["Structure & Flow"] == 8


@pytest.mark.asyncio
async def test_evaluator_retry_on_invalid_json(standard_rubric):
    valid_payload = {
        "scores": {
            "Content & Accuracy": 6,
            "Structure & Flow": 6,
            "Examples & Case Studies": 6
        },
        "overall_score": 6.0,
        "notes": "Passable attempt after retry."
    }

    bad_resp = MagicMock()
    bad_resp.status_code = 200
    bad_resp.json.return_value = {
        "choices": [{"message": {"content": "This is plain text, not JSON."}}]
    }

    good_resp = MagicMock()
    good_resp.status_code = 200
    good_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(valid_payload)}}]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [bad_resp, good_resp]
        result = await evaluate(
            submitted_answer="Student answer",
            question_text="Question text",
            model_answer="Model answer",
            rubric_criteria=standard_rubric,
            retry=True,
        )
        assert result["overall_score"] == 6.0
        assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_evaluator_429_rate_limit_fallback(standard_rubric):
    mock_resp = MagicMock()
    mock_resp.status_code = 429

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await evaluate(
            submitted_answer="Student answer",
            question_text="Question text",
            model_answer="Model answer",
            rubric_criteria=standard_rubric,
        )

        assert result["overall_score"] == 6.0
        assert "429" in result["notes"]
        assert all(v == 6 for v in result["scores"].values())


# ── Feedback Agent Tests ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_feedback_agent_english():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Strong grasp of constitutional articles. Incorporate Sarkaria Commission."}}]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        feedback = await generate_feedback(
            scores_json={"Content": 8},
            evaluator_notes="Good answer",
            question_text="Discuss federalism",
            language="en",
        )
        assert "Sarkaria" in feedback
        sent_payload = mock_post.call_args[1]["json"]
        assert "English" in sent_payload["messages"][0]["content"]


@pytest.mark.asyncio
async def test_feedback_agent_hindi_routing():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "आपका उत्तर बहुत प्रभावी है। नीति आयोग का संदर्भ अवश्य जोड़ें।"}}]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        feedback = await generate_feedback(
            scores_json={"Content": 8},
            evaluator_notes="Good answer",
            question_text="Discuss federalism",
            language="hi",
        )
        assert "उत्तर" in feedback
        sent_payload = mock_post.call_args[1]["json"]
        assert "Hindi" in sent_payload["messages"][0]["content"]


@pytest.mark.asyncio
async def test_feedback_agent_tamil_routing():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "உங்கள் பதில் மிகச் சிறப்பாக உள்ளது. நிதிக்குழுவின் பரிந்துரைகளைச் சேர்க்கவும்."}}]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        feedback = await generate_feedback(
            scores_json={"Content": 8},
            evaluator_notes="Good answer",
            question_text="Discuss federalism",
            language="ta",
        )
        assert "பதில்" in feedback
        sent_payload = mock_post.call_args[1]["json"]
        assert "Tamil" in sent_payload["messages"][0]["content"]


@pytest.mark.asyncio
async def test_translate_model_answer_en_passthrough():
    text = "Cooperative federalism requires active consultation..."
    translated = await translate_model_answer(text, language="en")
    assert translated == text


@pytest.mark.asyncio
async def test_translate_model_answer_indic():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "सहकारी संघवाद में केंद्र और राज्यों के बीच संवाद आवश्यक है।"}}]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await translate_model_answer("English text", language="hi")
        assert "सहकारी" in result


# ── Orchestrator Pipeline Tests ────────────────────────────────────

@pytest.mark.asyncio
async def test_orchestrator_pipeline_retrieval_fallback():
    db = SessionLocal()
    try:
        with patch("agents.orchestrator.retrieve") as mock_ret, \
             patch("agents.orchestrator.evaluate", new_callable=AsyncMock) as mock_eval, \
             patch("agents.orchestrator.generate_feedback", new_callable=AsyncMock) as mock_feed:

            mock_ret.return_value = {"error": "Question too dissimilar"}
            mock_eval.return_value = {
                "scores": {"coverage": 6, "structure": 6, "examples": 6, "word_limit_adherence": 6, "time_management": 6},
                "overall_score": 6.0,
                "notes": "Evaluated against general baseline"
            }
            mock_feed.return_value = "Good effort on a novel question."

            result = await run_evaluate_pipeline(
                question_text="A completely novel question not in syllabus",
                answer_text="Here is my structured answer addressing the prompt with relevant context and points.",
                language="en",
                db=db,
            )

            assert result["matched_question"] == "A completely novel question not in syllabus"
            assert result["overall_score"] == 6.0
            assert "attempt_id" in result

            saved = db.query(Attempt).filter(Attempt.id == result["attempt_id"]).first()
            assert saved is not None
            assert saved.pyq_id == "unknown"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_orchestrator_pipeline_persists_in_db():
    db = SessionLocal()
    try:
        with patch("agents.orchestrator.retrieve") as mock_ret, \
             patch("agents.orchestrator.evaluate", new_callable=AsyncMock) as mock_eval, \
             patch("agents.orchestrator.generate_feedback", new_callable=AsyncMock) as mock_feed:

            mock_ret.return_value = {
                "pyq_id": "test-pyq-1",
                "topic_id": "test-gs2-federalism",
                "question_text": "Discuss federalism",
                "model_answer": "Model answer",
                "key_points": ["Point A"],
                "word_limit": 250,
                "year": 2021,
                "difficulty": "moderate",
                "similarity_score": 0.90,
            }
            mock_eval.return_value = {
                "scores": {"Content & Accuracy": 9, "Structure & Flow": 8, "Examples & Case Studies": 8, "Word Count & Time": 9},
                "overall_score": 8.6,
                "notes": "Outstanding depth"
            }
            mock_feed.return_value = "Excellent work on this attempt!"

            result = await run_evaluate_pipeline(
                question_text="Discuss federalism",
                answer_text="Cooperative federalism requires mutual trust and institutional stability between parties.",
                language="en",
                db=db,
                time_taken_seconds=360,
            )

            attempt_id = result["attempt_id"]
            saved_attempt = db.query(Attempt).filter(Attempt.id == attempt_id).first()
            assert saved_attempt is not None
            assert saved_attempt.overall_score == 8.6
            assert saved_attempt.time_taken_seconds == 360
    finally:
        db.close()


# ── Validation & Settings Tests ────────────────────────────────────

def test_validate_evaluation_empty_criterion(standard_rubric):
    bad_data = {
        "scores": {},
        "overall_score": 5.0,
        "notes": "Empty"
    }
    with pytest.raises(ValueError, match="Missing scores for criteria"):
        _validate_evaluation(bad_data, standard_rubric)


def test_validate_evaluation_negative_score(standard_rubric):
    bad_data = {
        "scores": {
            "Content & Accuracy": -1,
            "Structure & Flow": 7,
            "Examples & Case Studies": 7
        },
        "overall_score": 5.0,
        "notes": "Negative"
    }
    with pytest.raises(ValueError, match="must be 0-10"):
        _validate_evaluation(bad_data, standard_rubric)


def test_pydantic_settings_instantiation():
    custom_settings = Settings(
        OPENROUTER_MODEL="custom-model-test",
        OPENROUTER_API_KEY="test-key",
    )
    assert custom_settings.OPENROUTER_MODEL == "custom-model-test"
    assert custom_settings.OPENROUTER_API_KEY == "test-key"
    assert "en" in custom_settings.LANGUAGE_MAP
