"""
SuperKalam Application Configuration
Loads environment variables and provides app-wide settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    """Application settings loaded from environment variables."""

    # Project paths
    PROJECT_ROOT: Path = PROJECT_ROOT
    DB_DIR: Path = PROJECT_ROOT / "db"
    CHROMA_DIR: Path = PROJECT_ROOT / os.getenv("CHROMA_PERSIST_DIR", "chroma_db")
    SEED_DATA_PATH: Path = PROJECT_ROOT / "data" / "seed_data.json"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'db' / 'superkalam.db'}")

    # OpenRouter LLM
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1/chat/completions"

    # Retrieval
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHROMA_COLLECTION: str = "superkalam_pyqs"

    # Language map
    LANGUAGE_MAP: dict = {
        "en": "English",
        "hi": "Hindi (हिन्दी)",
        "ta": "Tamil (தமிழ்)",
    }

    # Rubric defaults (weights must sum to 1.0)
    DEFAULT_RUBRIC_WEIGHTS: dict = {
        "coverage": 0.40,
        "structure": 0.25,
        "examples": 0.20,
        "word_limit_adherence": 0.15,
    }

    # API
    APP_TITLE: str = "SuperKalam — UPSC Mains Answer Evaluator"
    APP_DESCRIPTION: str = (
        "Agentic multi-lingual UPSC Mains answer evaluator. "
        "Submit your answer to get rubric-based scores and mentor-style feedback "
        "in English, Hindi, or Tamil."
    )
    APP_VERSION: str = "1.0.0"


settings = Settings()
