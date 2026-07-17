"""
SuperKalam Database Setup
SQLAlchemy models and session management for SQLite persistence.
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from app.config import settings

# Ensure db directory exists
settings.DB_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite-specific
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ─── ORM Models ───────────────────────────────────────────────

class Topic(Base):
    """UPSC GS paper topic (seeded from seed_data.json)."""
    __tablename__ = "topics"

    id = Column(String, primary_key=True)           # e.g. "gs2-federalism"
    paper = Column(String, nullable=False)           # e.g. "GS Paper II"
    title = Column(String, nullable=False)           # e.g. "Federalism & Centre-State Relations"
    syllabus_note = Column(Text, default="")

    # Relationships
    pyqs = relationship("PYQ", back_populates="topic", lazy="selectin")
    rubric = relationship("Rubric", back_populates="topic", uselist=False, lazy="selectin")


class PYQ(Base):
    """Previous Year Question with model answer."""
    __tablename__ = "pyqs"

    id = Column(String, primary_key=True)            # e.g. "gs2-fed-2020-q1"
    topic_id = Column(String, ForeignKey("topics.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    year = Column(Integer, nullable=True)
    model_answer = Column(Text, nullable=False)
    key_points = Column(Text, default="[]")          # JSON string of key points
    word_limit = Column(Integer, default=250)
    difficulty = Column(String, default="moderate")

    # Relationships
    topic = relationship("Topic", back_populates="pyqs")


class Rubric(Base):
    """Evaluation rubric per topic — stored as JSON for flexibility."""
    __tablename__ = "rubrics"

    topic_id = Column(String, ForeignKey("topics.id"), primary_key=True)
    criteria_json = Column(Text, nullable=False)
    # Format: [{"name": "coverage", "weight": 0.40, "description": "..."}, ...]

    # Relationships
    topic = relationship("Topic", back_populates="rubric")


class Attempt(Base):
    """A student's evaluation attempt — generated at runtime."""
    __tablename__ = "attempts"

    id = Column(String, primary_key=True)             # UUID
    topic_id = Column(String, ForeignKey("topics.id"), nullable=False)
    pyq_id = Column(String, ForeignKey("pyqs.id"), nullable=False)
    submitted_answer = Column(Text, nullable=False)
    language = Column(String, nullable=False)          # 'en' | 'hi' | 'ta'
    scores_json = Column(Text, nullable=False)         # Per-criterion scores
    overall_score = Column(Float, nullable=False)
    feedback_text = Column(Text, nullable=False)       # In requested language
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    topic = relationship("Topic")
    pyq = relationship("PYQ")


# ─── Database Utilities ───────────────────────────────────────

def create_tables():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency — yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
