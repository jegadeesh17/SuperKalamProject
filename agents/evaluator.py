"""
Evaluator Agent — LLM-based answer scoring
Scores a student's answer against the rubric using strict JSON output.
"""

import json
import httpx

from app.config import settings


EVALUATOR_SYSTEM_PROMPT = """You are a UPSC Mains answer evaluator. You evaluate student answers with the precision and fairness of an experienced UPSC examiner.

Score the submitted answer against each rubric criterion (0-10 scale). Compare against the model answer for content accuracy, but do not penalize different valid perspectives or approaches.

Scoring guide:
- 0-2: Very poor — missing most key content, no structure
- 3-4: Below average — partial coverage, weak structure
- 5-6: Average — decent coverage with gaps, acceptable structure
- 7-8: Good — strong coverage, clear structure, relevant examples
- 9-10: Excellent — comprehensive, well-structured, insightful examples

Return ONLY valid JSON, no markdown fences, no commentary, no extra text.

Schema:
{
  "scores": {"<criterion_name>": <0-10 integer>, ...},
  "overall_score": <weighted average, 0-10 float rounded to 1 decimal>,
  "notes": "<2-3 sentence internal note for the feedback agent, in English>"
}"""


def _build_evaluation_prompt(
    submitted_answer: str,
    question_text: str,
    model_answer: str,
    rubric_criteria: list[dict],
    word_limit: int,
) -> str:
    """Build the user prompt for the evaluator LLM call."""
    criteria_text = "\n".join(
        f"- {c['name']} (weight: {c['weight']:.0%}): {c['description']}"
        for c in rubric_criteria
    )

    return f"""QUESTION:
{question_text}

MODEL ANSWER (reference — do not penalize valid alternative perspectives):
{model_answer}

STUDENT'S SUBMITTED ANSWER:
{submitted_answer}

RUBRIC CRITERIA:
{criteria_text}

WORD LIMIT: {word_limit} words
ACTUAL WORD COUNT: {len(submitted_answer.split())} words

Score the student's answer against EACH criterion (0-10). Calculate the weighted overall score. Write 2-3 sentences of evaluator notes for the feedback agent.

Return ONLY valid JSON."""


async def evaluate(
    submitted_answer: str,
    question_text: str,
    model_answer: str,
    rubric_criteria: list[dict],
    word_limit: int = 250,
    retry: bool = True,
) -> dict:
    """
    Evaluator Agent: scores a student's answer using the LLM.

    Input:  submitted_answer, question context, rubric
    Output: dict with scores, overall_score, notes
    Raises: ValueError on parse failure after retry
    """
    user_prompt = _build_evaluation_prompt(
        submitted_answer, question_text, model_answer, rubric_criteria, word_limit
    )

    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": EVALUATOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,  # Low temperature for consistent scoring
        "max_tokens": 500,
    }

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://superkalam.demo",
        "X-Title": "SuperKalam Evaluator",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            settings.OPENROUTER_BASE_URL,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

    result = response.json()
    content = result["choices"][0]["message"]["content"].strip()

    # Clean markdown fences if the model disobeys
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        parsed = json.loads(content)
        _validate_evaluation(parsed, rubric_criteria)
        return parsed
    except (json.JSONDecodeError, ValueError) as e:
        if retry:
            # Retry once with stricter instructions
            stricter_prompt = (
                user_prompt
                + "\n\nCRITICAL: Your previous response was not valid JSON. "
                "Return ONLY a JSON object with 'scores', 'overall_score', and 'notes'. "
                "No other text."
            )
            payload["messages"][1]["content"] = stricter_prompt
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    settings.OPENROUTER_BASE_URL,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()

            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            parsed = json.loads(content)
            _validate_evaluation(parsed, rubric_criteria)
            return parsed
        else:
            raise ValueError(
                f"Evaluator LLM returned invalid JSON after retry: {e}\nRaw: {content}"
            )


def _validate_evaluation(parsed: dict, rubric_criteria: list[dict]) -> None:
    """Validate the evaluator's JSON output against expected schema."""
    if "scores" not in parsed:
        raise ValueError("Missing 'scores' in evaluator output")
    if "overall_score" not in parsed:
        raise ValueError("Missing 'overall_score' in evaluator output")
    if "notes" not in parsed:
        raise ValueError("Missing 'notes' in evaluator output")

    # Ensure all criteria are scored
    expected_criteria = {c["name"] for c in rubric_criteria}
    actual_criteria = set(parsed["scores"].keys())
    if not expected_criteria.issubset(actual_criteria):
        missing = expected_criteria - actual_criteria
        raise ValueError(f"Missing scores for criteria: {missing}")

    # Ensure scores are in range
    for name, score in parsed["scores"].items():
        if not (0 <= score <= 10):
            raise ValueError(f"Score for '{name}' is {score}, must be 0-10")
