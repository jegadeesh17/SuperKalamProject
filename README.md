# SuperKalam — Agentic UPSC Mains Evaluator

SuperKalam is a multi-lingual, agentic AI evaluator for UPSC Mains answer writing. It uses a chain of LLM agents and RAG (ChromaDB) to accurately score student answers against UPSC rubrics and provide mentor-style feedback in English, Hindi, and Tamil.

## Features

1. **Auto-Matching (Retrieval Agent)**: Paste any UPSC question. The system uses ChromaDB semantic search to match it to a known PYQ (Previous Year Question) and retrieve the official model answer and rubric.
2. **Strict Evaluation (Evaluator Agent)**: An LLM agent scores the answer (0-10) across four dimensions (Coverage, Structure, Examples, Word Limit) and enforces a strict JSON output contract.
3. **Localized Mentorship (Feedback Agent)**: Generates encouraging, actionable feedback natively in English, Hindi, or Tamil.
4. **Model Answer Mode**: Students can simply request the model answer for any PYQ.
5. **Modern Glassmorphic UI**: A responsive, premium web interface.

## Tech Stack

- **Backend**: FastAPI, Python 3.10+
- **Database**: SQLite (SQLAlchemy) for attempts/rubrics, ChromaDB for semantic search
- **LLM**: OpenRouter API (`meta-llama/llama-3.1-8b-instruct:free`)
- **Frontend**: HTML5, Vanilla CSS (Glassmorphism), Vanilla JS

## Local Setup

1. **Clone & Environment**:
   ```bash
   git clone https://github.com/jegadeesh17/SuperKalamProject.git
   cd SuperKalamProject
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Mac/Linux:
   source venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Secrets**:
   Copy `.env.example` to `.env` and add your OpenRouter API key.
   ```bash
   copy .env.example .env
   # Edit .env and set OPENROUTER_API_KEY
   ```

4. **Ingest Seed Data**:
   This creates the SQLite database and populates ChromaDB with the 40 UPSC PYQs and their model answers.
   ```bash
   python -m data.ingest
   ```

5. **Run the App**:
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Access the App**:
   - Web UI: http://127.0.0.1:8000/ui/
   - API Docs (Swagger): http://127.0.0.1:8000/docs

## API Architecture

The project uses a clean modular structure. The core logic lives in `agents/`:
- `retrieval.py`: Embeds the student's question and finds the nearest PYQ match.
- `evaluator.py`: Prompts the LLM with the rubric and model answer, enforcing a JSON schema for scores.
- `feedback.py`: Translates evaluator notes into empathetic, localized mentor feedback.
- `orchestrator.py`: Chains these agents together.

## Built By
Jegadeesh
