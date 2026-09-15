"""
Integration tests for SuperKalam FastAPI endpoints.
Tests validation, error handling, and end-to-end mock test evaluation.
"""

from unittest.mock import patch, AsyncMock
import pytest


def test_get_random_question(client):
    response = client.get("/api/random-question")
    assert response.status_code == 200
    data = response.json()
    assert "question_text" in data
    assert "word_limit" in data
    assert data["word_limit"] > 0


def test_evaluate_input_too_short_rejected(client):
    # answer_text min_length is 20
    payload = {
        "question_text": "Discuss the challenges to cooperative federalism in India.",
        "answer_text": "Too short",
        "language": "en"
    }
    response = client.post("/api/evaluate", json=payload)
    assert response.status_code == 422  # Pydantic validation error


def test_evaluate_invalid_language_rejected(client):
    payload = {
        "question_text": "Discuss the challenges to cooperative federalism in India.",
        "answer_text": "This is a sufficiently long student answer meeting the twenty character minimum length requirement.",
        "language": "fr"  # Invalid language, only 'en', 'hi', 'ta' allowed
    }
    response = client.post("/api/evaluate", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_evaluate_pipeline_mocked_success(client, mock_evaluator_response, mock_feedback_response):
    payload = {
        "question_text": "Discuss the challenges to cooperative federalism in India with suitable examples.",
        "answer_text": "Cooperative federalism in India has faced significant challenges in recent years, especially concerning fiscal relations and GST compensation cess...",
        "language": "en",
        "time_taken_seconds": 480
    }

    with patch("agents.orchestrator.retrieve") as mock_ret, \
         patch("agents.orchestrator.evaluate", new_callable=AsyncMock) as mock_eval, \
         patch("agents.orchestrator.generate_feedback", new_callable=AsyncMock) as mock_feed:

        mock_ret.return_value = {
            "pyq_id": "test-pyq-1",
            "topic_id": "test-gs2-federalism",
            "question_text": "Discuss the challenges to cooperative federalism in India with suitable examples.",
            "model_answer": "Cooperative federalism requires active consultation...",
            "key_points": ["GST Council", "Inter-State Council"],
            "word_limit": 250,
            "year": 2021,
            "difficulty": "moderate",
            "similarity_score": 0.88,
        }
        mock_eval.return_value = mock_evaluator_response
        mock_feed.return_value = mock_feedback_response

        response = client.post("/api/evaluate", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert "attempt_id" in data
        assert "overall_score" in data
        assert data["overall_score"] == 7.9
        assert "scores" in data
        assert "feedback" in data
        assert data["scores"]["Content & Accuracy"] == 8


def test_get_topics_endpoint(client):
    response = client.get("/api/topics")
    assert response.status_code == 200
    topics = response.json()
    assert isinstance(topics, list)
    assert len(topics) > 0


def test_get_attempts_endpoint(client):
    response = client.get("/api/attempts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
