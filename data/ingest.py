"""
Seed Data Ingestion Script
Loads seed_data.json into SQLite and ChromaDB.
"""

import json
import logging
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

from app.config import settings
from app.database import SessionLocal, create_tables, Topic, Rubric, PYQ

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def ingest_data():
    """Load JSON seed data into SQLite and ChromaDB."""
    logger.info(f"Loading seed data from {settings.SEED_DATA_PATH}")
    
    if not settings.SEED_DATA_PATH.exists():
        logger.error("Seed data file not found!")
        return

    with open(settings.SEED_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # ── 1. Setup SQLite ──
    create_tables()
    db = SessionLocal()

    # Clear existing data (for idempotency)
    logger.info("Clearing existing SQLite data...")
    db.query(PYQ).delete()
    db.query(Rubric).delete()
    db.query(Topic).delete()
    db.commit()

    # Load Topics
    logger.info("Loading topics...")
    for t_data in data.get("topics", []):
        topic = Topic(
            id=t_data["id"],
            paper=t_data["paper"],
            title=t_data["title"],
            syllabus_note=t_data.get("syllabus_note", "")
        )
        db.add(topic)
    
    # Load Rubrics
    logger.info("Loading rubrics...")
    for r_data in data.get("rubrics", []):
        rubric = Rubric(
            topic_id=r_data["topic_id"],
            criteria_json=json.dumps(r_data["criteria"])
        )
        db.add(rubric)

    # Load PYQs
    logger.info("Loading PYQs...")
    pyq_docs = []
    pyq_metadatas = []
    pyq_ids = []

    for p_data in data.get("pyqs", []):
        pyq = PYQ(
            id=p_data["id"],
            topic_id=p_data["topic_id"],
            question_text=p_data["question_text"],
            year=p_data.get("year"),
            model_answer=p_data["model_answer"],
            key_points=json.dumps(p_data.get("key_points", [])),
            word_limit=p_data.get("word_limit", 250),
            difficulty=p_data.get("difficulty", "moderate")
        )
        db.add(pyq)

        # Prepare for ChromaDB
        pyq_docs.append(p_data["question_text"])
        pyq_ids.append(p_data["id"])
        pyq_metadatas.append({
            "topic_id": p_data["topic_id"],
            "year": p_data.get("year", 0),
            "model_answer": p_data["model_answer"],
            "key_points": json.dumps(p_data.get("key_points", [])),
            "word_limit": p_data.get("word_limit", 250),
            "difficulty": p_data.get("difficulty", "moderate")
        })

    db.commit()
    db.close()
    logger.info("SQLite ingestion complete.")

    # ── 2. Setup ChromaDB ──
    logger.info(f"Setting up ChromaDB at {settings.CHROMA_DIR}...")
    
    # Optional: clear existing collection to prevent duplicates if re-running
    chroma_client = chromadb.PersistentClient(path=str(settings.CHROMA_DIR))
    try:
        chroma_client.delete_collection(name=settings.CHROMA_COLLECTION)
        logger.info("Deleted existing ChromaDB collection.")
    except Exception:
        pass

    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=settings.EMBEDDING_MODEL
    )
    
    collection = chroma_client.create_collection(
        name=settings.CHROMA_COLLECTION,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"}
    )

    logger.info(f"Generating embeddings for {len(pyq_docs)} questions (this may take a minute)...")
    collection.add(
        documents=pyq_docs,
        metadatas=pyq_metadatas,
        ids=pyq_ids
    )
    
    logger.info("ChromaDB ingestion complete!")
    logger.info("All seed data successfully loaded. You can now run the app.")

if __name__ == "__main__":
    ingest_data()
