"""
SuperKalam Application Configuration (Production Grade)
Powered by Pydantic-Settings with environment validation and strict typing.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Project paths
    PROJECT_ROOT: Path = _BASE_DIR
    DB_DIR: Path = _BASE_DIR / "db"
    CHROMA_DIR: Path = _BASE_DIR / "chroma_db"
    SEED_DATA_PATH: Path = _BASE_DIR / "data" / "seed_data.json"

    # Database
    DATABASE_URL: str = Field(
        default=f"sqlite:///{_BASE_DIR / 'db' / 'superkalam.db'}",
        description="SQLAlchemy database connection URI",
    )

    # LLM Gateway (Groq / OpenRouter)
    OPENROUTER_API_KEY: str = Field(
        default="",
        description="API key for Groq / OpenRouter LLM gateway",
    )
    OPENROUTER_MODEL: str = Field(
        default="llama-3.3-70b-versatile",
        description="Default LLM model identifier",
    )
    OPENROUTER_BASE_URL: str = Field(
        default="https://api.groq.com/openai/v1/chat/completions",
        description="LLM chat completions endpoint URL",
    )

    # Retrieval & ChromaDB
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHROMA_COLLECTION: str = "superkalam_pyqs"

    # Supported Language Map
    LANGUAGE_MAP: Dict[str, str] = {
        "en": "English",
        "hi": "Hindi (हिन्दी)",
        "ta": "Tamil (தமிழ்)",
    }

    # Rubric Defaults
    DEFAULT_RUBRIC_WEIGHTS: Dict[str, float] = {
        "coverage": 0.35,
        "structure": 0.25,
        "examples": 0.20,
        "word_limit_adherence": 0.10,
        "time_management": 0.10,
    }

    # API Metadata
    APP_TITLE: str = "SuperKalam — UPSC Mains Answer Evaluator"
    APP_DESCRIPTION: str = (
        "Agentic multi-lingual UPSC Mains answer evaluator. "
        "Submit your answer to get rubric-based scores and mentor-style feedback "
        "in English, Hindi, or Tamil."
    )
    APP_VERSION: str = "2.0.0"


_settings_instance = None


def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


settings = get_settings()
