"""
Retrieval Agent — ChromaDB similarity search
Finds the closest PYQ match for a student's submitted question.
"""

import json
import chromadb
from chromadb.utils import embedding_functions

from app.config import settings


# Module-level client (initialized once)
_chroma_client = None
_collection = None


def _get_collection():
    """Lazy-initialize ChromaDB client and collection."""
    global _chroma_client, _collection
    if _collection is None:
        _chroma_client = chromadb.PersistentClient(path=str(settings.CHROMA_DIR))
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.EMBEDDING_MODEL
        )
        _collection = _chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def retrieve(question_text: str, top_k: int = 1) -> dict:
    """
    Retrieval Agent: finds the closest PYQ to the submitted question.

    Input:  question_text (str) — the student's question
    Output: dict with keys:
        - pyq_id, topic_id, question_text, model_answer,
          key_points, word_limit, year, similarity_score
    """
    collection = _get_collection()

    results = collection.query(
        query_texts=[question_text],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    if not results["ids"][0]:
        return {"error": "No matching question found in the database."}

    # ChromaDB returns cosine distance; convert to similarity
    best_match_idx = 0
    metadata = results["metadatas"][0][best_match_idx]
    distance = results["distances"][0][best_match_idx]
    similarity = 1.0 - distance  # cosine distance → similarity

    return {
        "pyq_id": results["ids"][0][best_match_idx],
        "topic_id": metadata.get("topic_id", ""),
        "question_text": results["documents"][0][best_match_idx],
        "model_answer": metadata.get("model_answer", ""),
        "key_points": json.loads(metadata.get("key_points", "[]")),
        "word_limit": int(metadata.get("word_limit", 250)),
        "year": int(metadata.get("year", 0)) if metadata.get("year") else None,
        "difficulty": metadata.get("difficulty", "moderate"),
        "similarity_score": round(similarity, 4),
    }


def retrieve_by_id(pyq_id: str) -> dict | None:
    """Retrieve a specific PYQ by its ID from ChromaDB."""
    collection = _get_collection()

    results = collection.get(
        ids=[pyq_id],
        include=["documents", "metadatas"],
    )

    if not results["ids"]:
        return None

    metadata = results["metadatas"][0]
    return {
        "pyq_id": pyq_id,
        "topic_id": metadata.get("topic_id", ""),
        "question_text": results["documents"][0],
        "model_answer": metadata.get("model_answer", ""),
        "key_points": json.loads(metadata.get("key_points", "[]")),
        "word_limit": int(metadata.get("word_limit", 250)),
        "year": int(metadata.get("year", 0)) if metadata.get("year") else None,
        "difficulty": metadata.get("difficulty", "moderate"),
    }
