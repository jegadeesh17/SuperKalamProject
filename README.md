# SuperKalam — Agentic UPSC Mock Test Platform

SuperKalam is a multi-lingual, agentic AI mock test platform for UPSC Mains answer writing. It gives students timed mock tests using Previous Year Questions (PYQs), scores their answers against a rubric with an LLM, and returns mentor-style feedback in English, Hindi, or Tamil.

Live demo: https://superkalam-api-242711953247.asia-south1.run.app/app

## Features

- **Mock test generation**: the web UI fetches a random PYQ from the seeded database (60 questions across 5 topics) and runs a timed attempt. The API can also take any pasted UPSC question and match it to the closest known PYQ with ChromaDB semantic search (cosine similarity of at least 0.50).
- **Rubric evaluation (Evaluator Agent)**: an LLM scores the answer from 0 to 10 per rubric criterion and returns strict JSON that is validated with a Pydantic model. The seeded rubric has four dimensions: coverage (0.40), structure (0.25), examples (0.20) and word limit adherence (0.15). A question that matches no seeded PYQ uses a five-criterion default rubric instead (`DEFAULT_RUBRIC_WEIGHTS`, `agents/orchestrator.py:58`; see `docs/SPEC.md` §3.2).
- **Localized mentorship (Feedback Agent)**: feedback is generated in English, Hindi or Tamil. The language is enforced in the prompt ("Respond ENTIRELY in ... native script"), not checked after generation.
- **Model answer endpoint**: `POST /api/model-answer` returns the matched PYQ's model answer, translated for Hindi or Tamil. The web UI does not have a model-answer mode; it is API only.
- **Rate-limit fallback**: on an HTTP 429 from the LLM, the evaluator returns mock scores of 6 for every criterion instead of failing. This is a per-request fallback, not a circuit breaker.
- **Web UI**: a static HTML/CSS/JS page served at `/app` (also at `/ui`).

The seed data (`data/seed_data.json`) holds 60 PYQs: 40 real questions and 20 synthetic ones whose ids start with `mock-pyq-`.

## Quick start

Prerequisites: Python 3.11 (the version used by the Dockerfile) and a Groq API key.

```bash
git clone https://github.com/jegadeesh17/SuperKalamProject.git
cd SuperKalamProject
python -m venv .venv
source .venv/Scripts/activate   # Git Bash on Windows; use .venv/bin/activate on Mac/Linux
pip install -r requirements.txt
cp .env.example .env            # then set OPENROUTER_API_KEY (a Groq key by default)
python -m data.ingest           # creates the SQLite DB and the ChromaDB collection
uvicorn app.main:app --reload
```

The app also seeds an empty database on startup. Open http://127.0.0.1:8000/app/ for the UI or http://127.0.0.1:8000/docs for the Swagger docs. The Docker image seeds data at build time and listens on `$PORT` (default 8080).

## Usage

Check the service is up (no API key needed):

```bash
curl http://127.0.0.1:8000/health
```

```json
{"status":"healthy","service":"SuperKalam Answer Evaluator","version":"2.0.0","database":true}
```

Evaluate an answer (needs a working LLM key). Response shape, from `EvaluateResponse` in `app/models.py`:

```bash
curl -X POST http://127.0.0.1:8000/api/evaluate \
  -H "Content-Type: application/json" \
  -d '{"question_text": "Discuss the role of cooperative federalism in India governance.", "answer_text": "Cooperative federalism rests on shared responsibility between the Union and the states, ...", "language": "en", "time_taken_seconds": 420}'
```

```json
{
  "attempt_id": "<uuid>",
  "matched_question": "<closest PYQ text>",
  "topic": "<topic title>",
  "year": 2020,
  "scores": {"coverage": 7, "structure": 6, "examples": 5, "word_limit_adherence": 8},
  "overall_score": 6.5,
  "feedback": "<mentor feedback in the requested language>",
  "language": "en"
}
```

API routes (all under `/api` except `/health` and the UI):

| Route | Purpose |
| --- | --- |
| `GET /api/random-question` | Random PYQ for a mock test (404 if the table is empty) |
| `POST /api/evaluate` | Full pipeline: retrieve, score, feedback, save attempt |
| `POST /api/model-answer` | Matched PYQ's model answer in `en`, `hi` or `ta` |
| `GET /api/topics` | Topics with question counts |
| `GET /api/topics/{topic_id}/questions` | PYQs of a topic |
| `GET /api/questions/{question_id}` | One PYQ with model answer and key points |
| `GET /api/attempts` | Past attempts (`topic_id`, `limit` query params) |
| `GET /api/attempts/{attempt_id}` | One past attempt |
| `GET /health` | Status, service, version and whether the DB file exists |
| `GET /app/`, `GET /ui/` | Web UI; `/` redirects to `/app/` |

## Running tests

```bash
.venv/Scripts/python -m pytest -q                     # full suite
.venv/Scripts/python -m pytest tests/test_agents.py -q  # one file
```

Measured on 2026-10-03 with `.venv/Scripts/python -m pytest -q`: 27 passed.

The tests mock the LLM HTTP calls, so they need no API key.

## Configuration

Settings are read from the environment or `.env` by `configs/settings.py`. See `.env.example` for the commented template.

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | (empty) | LLM gateway key. Despite the name, the default endpoint is Groq, so use a Groq key. Without it, evaluation fails with HTTP 422. |
| `OPENROUTER_MODEL` | `openai/gpt-oss-120b` | Model identifier sent to the gateway |
| `OPENROUTER_BASE_URL` | `https://api.groq.com/openai/v1/chat/completions` | Chat-completions endpoint |
| `DATABASE_URL` | `sqlite:///<project root>/db/superkalam.db` | SQLAlchemy URL |
| `CHROMA_DIR` | `<project root>/chroma_db` | ChromaDB persistent directory |
| `CHROMA_COLLECTION` | `superkalam_pyqs` | ChromaDB collection name |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers embedding model |

## Project structure

```
agents/      retrieval, evaluator, feedback agents and the orchestrator
app/         FastAPI app, routes, models, database, static web UI
configs/     pydantic-settings configuration
data/        seed_data.json, ingest.py, generate_pyqs.py
docs/        SPEC.md, DECISIONS.md and the docs index
notebooks/   exploration notebook
reports/     EVALUATOR_CALIBRATION.md (generated)
scripts/     calibrate_evaluator.py
tests/       pytest suite
.github/     Cloud Run deploy workflow
```

## Architecture

A three-agent pipeline chained by `agents/orchestrator.py`:

- `retrieval.py`: dense-only ChromaDB search (all-MiniLM-L6-v2, cosine); top match with similarity of at least 0.50.
- `evaluator.py`: prompts the LLM with the rubric and model answer and validates the JSON it returns. It retries once with a stricter prompt and strips markdown fences.
- `feedback.py`: turns the evaluator's notes into localized mentor feedback.

Attempts are stored in SQLite (SQLAlchemy); ChromaDB holds the PYQ embeddings. LLM calls use a flat 60-second timeout. The service is deployed to Google Cloud Run by `.github/workflows/deploy.yml` on every push to `main` or `master`. The workflow runs no tests. Details are in [docs/SPEC.md](docs/SPEC.md).

## Evaluation

`reports/EVALUATOR_CALIBRATION.md` reports Pearson 0.9551, Spearman 0.9736 and MAE 0.58. These measure a standalone keyword heuristic against author-assigned labels on synthetic answers, not the LLM evaluator against human graders. See Known limitations and `docs/SPEC.md` section 5.

## Known limitations

- The calibration report scores a heuristic against synthetic labels and makes no LLM calls. Its header says "40 PYQs / 120 passes", but the seed data has 60 PYQs. Its B-versus-C margin of +1.99 is marked as passing a 2.0 target. The report is generated and was not edited.
- On HTTP 429 the evaluator returns mock scores of 6 (HTTP 200) and the attempt is saved. The retry call, the feedback call and other non-2xx responses return HTTP 502.
- The deploy workflow runs no tests and redeploys on any push to `main` or `master`.
- Retrieval is dense-only, with no lexical matching, and the 0.50 threshold is fixed in code.
- The web UI has no model-answer mode; `POST /api/model-answer` is API only.
- The key and model settings keep their `OPENROUTER_*` names although the default endpoint is Groq.

## Documentation

- [Documentation index](docs/README.md)
- [System specification](docs/SPEC.md)
- [Architecture decisions](docs/DECISIONS.md)
- [Changelog](CHANGELOG.md)

## License

MIT. See [LICENSE](LICENSE).
