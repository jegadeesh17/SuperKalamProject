"""
Unit tests for the Evaluator Agent rubric validation and JSON parsing.
"""

import pytest
from agents.evaluator import _validate_evaluation, _build_evaluation_prompt


@pytest.fixture
def sample_rubric():
    return [
        {"name": "Content & Accuracy", "weight": 0.40, "description": "Subject accuracy"},
        {"name": "Structure & Flow", "weight": 0.30, "description": "Logical flow"},
        {"name": "Examples", "weight": 0.30, "description": "Case studies"}
    ]


def test_validate_evaluation_success(sample_rubric):
    valid_output = {
        "scores": {
            "Content & Accuracy": 8,
            "Structure & Flow": 7,
            "Examples": 9
        },
        "overall_score": 8.0,
        "notes": "Good answer with relevant examples."
    }
    # Should not raise
    _validate_evaluation(valid_output, sample_rubric)


def test_validate_evaluation_missing_criterion(sample_rubric):
    missing_criterion_output = {
        "scores": {
            "Content & Accuracy": 8,
            "Structure & Flow": 7
            # Missing "Examples"
        },
        "overall_score": 7.5,
        "notes": "Incomplete score output."
    }
    with pytest.raises(ValueError, match="Missing scores for criteria"):
        _validate_evaluation(missing_criterion_output, sample_rubric)


def test_validate_evaluation_score_out_of_bounds(sample_rubric):
    invalid_score_output = {
        "scores": {
            "Content & Accuracy": 12,  # Invalid: > 10
            "Structure & Flow": 7,
            "Examples": 5
        },
        "overall_score": 8.0,
        "notes": "Out of range."
    }
    with pytest.raises(ValueError, match="must be 0-10"):
        _validate_evaluation(invalid_score_output, sample_rubric)


def test_build_evaluation_prompt_contains_rubric_and_constraints(sample_rubric):
    prompt = _build_evaluation_prompt(
        submitted_answer="This is a test answer for UPSC Mains.",
        question_text="Discuss the challenges to federalism.",
        model_answer="Model answer content here.",
        rubric_criteria=sample_rubric,
        word_limit=250,
        time_taken_seconds=420
    )
    assert "Discuss the challenges to federalism." in prompt
    assert "Content & Accuracy" in prompt
    assert "WORD LIMIT: 250" in prompt
    assert "TIME TAKEN: 420 seconds" in prompt
