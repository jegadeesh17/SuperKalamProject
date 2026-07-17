"""
Feedback Agent — LLM-based mentor-style feedback generation
Generates localized, encouraging, actionable feedback in the requested language.
"""

import httpx

from app.config import settings


FEEDBACK_SYSTEM_PROMPT_TEMPLATE = """You are a warm, direct UPSC Mains mentor giving feedback to a student.
Based on the evaluation scores and notes provided, write 4-6 sentences of feedback:
1. Start with what the student did well (be specific, cite from their answer)
2. Identify 1-2 specific areas for improvement
3. End with one concrete, actionable tip for their next attempt

Respond ENTIRELY in {language_name}, using native script (not transliteration).
Use terminology a UPSC aspirant would recognize from standard prep material.
Keep the tone encouraging but honest — like a mentor who cares about the student's success.

Do NOT include scores or numbers in the feedback — the scores are shown separately.
Do NOT use bullet points — write flowing, natural paragraphs."""


async def generate_feedback(
    scores_json: dict,
    evaluator_notes: str,
    question_text: str,
    language: str = "en",
) -> str:
    """
    Feedback Agent: generates mentor-style feedback in the requested language.

    Input:  scores, evaluator notes, question context, language code
    Output: plain text feedback string in the requested language
    """
    language_name = settings.LANGUAGE_MAP.get(language, "English")

    system_prompt = FEEDBACK_SYSTEM_PROMPT_TEMPLATE.format(
        language_name=language_name
    )

    user_prompt = f"""QUESTION EVALUATED:
{question_text}

EVALUATION SCORES: {scores_json}

EVALUATOR'S NOTES: {evaluator_notes}

Write your mentor feedback in {language_name} ({language}). Use native script."""

    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,  # Higher temperature for natural, varied feedback
        "max_tokens": 600,
    }

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://superkalam.demo",
        "X-Title": "SuperKalam Feedback",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            settings.OPENROUTER_BASE_URL,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

    result = response.json()
    feedback = result["choices"][0]["message"]["content"].strip()

    return feedback


async def translate_model_answer(
    model_answer: str,
    language: str = "en",
) -> str:
    """
    Translate/localize a model answer to the requested language.
    If language is 'en', returns the original answer unchanged.
    """
    if language == "en":
        return model_answer

    language_name = settings.LANGUAGE_MAP.get(language, "English")

    system_prompt = f"""You are an expert translator specializing in UPSC exam content.
Translate the following model answer into {language_name}, using native script.
Maintain the academic tone, keep proper nouns and technical terms intact,
and ensure the translation reads naturally to a UPSC aspirant studying in {language_name}.
Do NOT transliterate — use native script ({language_name}).
Return ONLY the translated text, no commentary."""

    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": model_answer},
        ],
        "temperature": 0.3,
        "max_tokens": 1000,
    }

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://superkalam.demo",
        "X-Title": "SuperKalam Translate",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            settings.OPENROUTER_BASE_URL,
            json=payload,
            headers=headers,
        )
        if response.status_code == 429:
            return "[MOCK] API Rate Limit Exceeded (429). The system is temporarily unable to generate personalized LLM feedback. Please try again later when the rate limit resets."
        response.raise_for_status()

    result = response.json()
    return result["choices"][0]["message"]["content"].strip()
