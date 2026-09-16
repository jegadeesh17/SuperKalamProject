# SuperKalam — System Specification

> Living spec for the SuperKalam agentic UPSC Mains answer evaluator. Update this file
> whenever the agent pipeline, output contract, or failure-handling behavior changes.

---

## 1. Problem Statement

UPSC Civil Services Mains aspirants need frequent, high-quality answer-writing practice,
but human evaluation of Mains-style answers is slow, expensive, and inconsistent — and
often unavailable at the odd hours (late night / early morning) aspirants actually study.

SuperKalam is a multi-lingual, agentic mock-test platform that acts as an always-available
answer evaluator:

1. A student takes a timed mock test against a randomly assigned Previous Year Question
   (PYQ), or pastes an arbitrary question of their own.
2. The student submits a written answer.
3. The system matches the question to the closest known PYQ, scores the submitted answer
   against that PYQ's official rubric using an LLM, and returns mentor-style feedback in
   the student's chosen language (English, Hindi, or Tamil).

Target persona: a self-studying UPSC aspirant who wants objective, rubric-based scoring
and encouraging, actionable feedback without waiting on a human evaluator.

---

## 2. Architecture

The system is a 3-agent pipeline, chained by `agents/orchestrator.py`
(`run_evaluate_pipeline` / `run_model_answer_pipeline`):

```
                POST /api/evaluate
                        │
                        ▼
        ┌───────────────────────────────┐
        │  1. Retrieval Agent            │   agents/retrieval.py
        │  Dense-only ChromaDB search    │
        │  (SentenceTransformer:         │
        │   all-MiniLM-L6-v2, cosine)    │
        └───────────────┬────────────────┘
                        │ matched PYQ, model answer,
                        │ rubric criteria, word limit
                        ▼
        ┌───────────────────────────────┐
        │  2. Evaluator Agent            │   agents/evaluator.py
        │  LLM rubric scoring            │
        │  (OpenRouter/Groq chat         │
        │   completions, strict JSON)    │
        └───────────────┬────────────────┘
                        │ scores, overall_score, notes
                        ▼
        ┌───────────────────────────────┐
        │  3. Feedback Agent             │   agents/feedback.py
        │  LLM mentor-style feedback,    │
        │  localized to en/hi/ta         │
        └───────────────┬────────────────┘
                        │
                        ▼
              Persist Attempt (SQLite)
                        │
                        ▼
              EvaluateResponse (JSON)
```

For `POST /api/model-answer`, the pipeline is Retrieval → Translation
(`agents/feedback.py::translate_model_answer`) only — the Evaluator Agent is not invoked.

### 2.1 Retrieval Agent (`agents/retrieval.py`)

- Dense-only similarity search against a ChromaDB `PersistentClient` collection
  (`superkalam_pyqs`), embedded with `SentenceTransformerEmbeddingFunction`
  (`all-MiniLM-L6-v2`), using cosine distance (`hnsw:space: cosine`).
- There is **no lexical/keyword (BM25/FTS) component** — matching is purely
  embedding-similarity based. This is a known limitation for questions containing exact
  identifiers (e.g. a specific Article number or Commission name) where dense-only
  retrieval can under- or mis-match; see §6.
- `retrieve(question_text, top_k=1)` converts the top ChromaDB cosine distance to a
  similarity score (`1.0 - distance`) and rejects matches below `similarity_score < 0.50`
  with `{"error": "Question is too different from known PYQs..."}`. The orchestrator
  treats this as a soft failure: it falls back to a generic rubric and a placeholder
  "no official model answer available" message rather than failing the request (see
  `agents/orchestrator.py::run_evaluate_pipeline`).

### 2.2 Evaluator Agent (`agents/evaluator.py`)

LLM-based rubric scoring via `evaluate()`. Calls the OpenRouter/Groq chat-completions
endpoint (`settings.OPENROUTER_BASE_URL`, default `openai/gpt-oss-120b` via
`settings.OPENROUTER_MODEL`) with `temperature=0.3` and `reasoning_effort="low"` (the
model is a reasoning model; without capping reasoning effort, hidden chain-of-thought can
consume the entire `max_tokens=500` budget and truncate the JSON output — see
`agents/evaluator.py:100-105`).

**The rubric criteria are dynamic, not fixed.** They are loaded per-topic from the
`Rubric` table (seeded from `data/seed_data.json`), so the evaluator's `scores` object is
validated as an open per-criterion mapping, not a hardcoded 4-field struct. As of this
writing, the seeded rubric criteria (see `data/seed_data.json:"rubrics"`) are, for every
topic:

| Criterion name          | Weight | What it measures |
| ------------------------ | -----: | ----------------- |
| `coverage`                | 0.40  | Key-concept recall against the model answer / syllabus anchor points |
| `structure`               | 0.25  | Introduction / body / conclusion structure and logical flow |
| `examples`                | 0.20  | Use of relevant examples, case studies, constitutional/statutory references |
| `word_limit_adherence`    | 0.15  | Adherence to the question's word limit (±10% target band) |

`configs/settings.py::DEFAULT_RUBRIC_WEIGHTS` is used only as part of the orchestrator's
fallback rubric when no `Rubric` row exists for a matched topic, and it is **not** simply
the seeded rubric plus one extra criterion — several of its weights differ from the seeded
values:

| Criterion name          | Seeded weight | `DEFAULT_RUBRIC_WEIGHTS` (fallback) weight |
| ------------------------ | -----------: | ------------------------------------------: |
| `coverage`                | 0.40        | 0.35 |
| `structure`               | 0.25        | 0.25 |
| `examples`                | 0.20        | 0.20 |
| `word_limit_adherence`    | 0.15        | 0.10 |
| `time_management`         | *(absent)*  | 0.10 |

So the fallback rubric both re-weights `coverage` (0.40 → 0.35) and `word_limit_adherence`
(0.15 → 0.10), and adds a 5th criterion, `time_management` (weight 0.10), which is not
present in any seeded rubric today. Tests (`tests/test_agents.py`, `tests/test_evaluator_rubric.py`) exercise the
pipeline with differently-named example criteria (e.g. `"Content & Accuracy"`,
`"Structure & Flow"`) precisely because criterion names are not hardcoded anywhere in the
evaluator — callers must not assume a fixed English label set.

#### Output contract

The Evaluator Agent's LLM call must return **strict JSON only** (no markdown fences, no
commentary — enforced by `EVALUATOR_SYSTEM_PROMPT`), matching this schema:

```json
{
  "scores": { "<criterion_name>": <0-10>, "...": "..." },
  "overall_score": <0-10, float, 1 decimal>,
  "notes": "<2-3 sentence internal note for the Feedback Agent>"
}
```

Required keys: `scores`, `overall_score`, `notes`. All three are checked for presence;
`scores` must be a mapping that is a superset of the active rubric's criterion names, and
every individual score must satisfy `0 <= score <= 10`. As of this change, this contract
is enforced via the `EvaluatorOutput` Pydantic model in `app/models.py`, invoked from
`agents/evaluator.py::_validate_evaluation()` (see §7 / P2 for the migration from the
previous hand-rolled dict checks — the criterion-subset check against the caller-supplied
rubric remains a manual check afterwards, because it depends on which rubric was active
for the request and cannot be expressed as a static Pydantic field).

Markdown code fences are stripped defensively before parsing
(`agents/evaluator.py:131-136`), since the system prompt asks the model not to emit them
but reasoning models sometimes do anyway.

### 2.3 Feedback Agent (`agents/feedback.py`)

- `generate_feedback()`: takes the evaluator's `scores`/`notes` and produces 4-6 sentences
  of mentor-style feedback in the requested language (`en`/`hi`/`ta`), via a
  language-specific system prompt (`FEEDBACK_SYSTEM_PROMPT_TEMPLATE`). No numeric scores
  are echoed back in the feedback text (scores are rendered separately by the frontend).
- `translate_model_answer()`: localizes the model answer text for the `/model-answer`
  route. Returns the original text unchanged for `language="en"` (no LLM call made in
  that case).

---

## 3. Non-Functional Requirements

### 3.1 Timeouts

Every outbound LLM call (`agents/evaluator.py`, `agents/feedback.py`) uses
`httpx.AsyncClient(timeout=60.0)` — a flat 60-second timeout, applied uniformly to the
connect + read + write + pool phases (`httpx`'s single-float `timeout=` shorthand). There
is currently no separate connect-timeout budget and no per-attempt backoff/jitter.

### 3.2 Retry policy (Evaluator Agent only)

`agents/evaluator.py::evaluate()` retries **exactly once** if the first LLM response
fails to parse as JSON or fails schema validation (`json.JSONDecodeError` or
`ValueError`/`ValidationError`, see `agents/evaluator.py:138-174`):

1. First attempt uses the normal `_build_evaluation_prompt()` output.
2. On failure, the retry re-sends the **same** user prompt with an appended stricter
   instruction block (`"CRITICAL: Your previous response was not valid JSON. ..."`),
   and re-parses/re-validates the response.
3. If the retry *also* fails to parse/validate, `evaluate()` raises
   `ValueError("Evaluator LLM returned invalid JSON after retry: ...")`, which propagates
   up through `agents/orchestrator.py` and is converted to an HTTP `422` by
   `app/routes/evaluate.py` (its `except ValueError` branch).
4. The retry call does **not** get 429-fallback handling — only the first attempt checks
   for a 429 (see §3.3); if the retry itself receives a non-2xx status,
   `response.raise_for_status()` raises `httpx.HTTPStatusError`, which is not caught by
   `evaluate()`'s `except (json.JSONDecodeError, ValueError)` and instead propagates up to
   the route's generic `except Exception` handler, returning HTTP `502`.
5. The Feedback Agent (`generate_feedback`, `translate_model_answer`) has **no retry
   logic** — a malformed or failed feedback call is not retried; failures there surface as
   `httpx.HTTPStatusError` → HTTP `502` from the route.

### 3.3 Rate-limit (429) fallback

Only the **first** Evaluator Agent call and `translate_model_answer` check for
`response.status_code == 429` before calling `raise_for_status()`
(`agents/evaluator.py:120-125`, `agents/feedback.py:142-144`). On a 429:

- **Evaluator**: returns a mock evaluation — every rubric criterion scored `6`,
  `overall_score: 6.0`, and `notes` prefixed `"[MOCK] API Rate Limit Exceeded (429)..."` —
  so the pipeline can still complete and persist an `Attempt` rather than hard-failing the
  request. This mock output is **not** run through `_validate_evaluation()` /
  `EvaluatorOutput` — it is constructed to already satisfy the contract by shape, so
  validation is skipped for this path.
- **`translate_model_answer`**: returns a plain-text `"[MOCK] API Rate Limit
  Exceeded (429)..."` string in place of the translated answer, rather than raising.
- `generate_feedback()` has **no** 429 fallback — a 429 there propagates via
  `raise_for_status()` to `httpx.HTTPStatusError` → HTTP `502`.
- The evaluator retry-on-invalid-JSON path also has no 429 fallback (see §3.2, point 4).

### 3.4 Retrieval threshold

`agents/retrieval.py::retrieve()` treats `similarity_score < 0.50` (cosine similarity, 1 −
cosine distance) as "no good match" and returns a soft error dict rather than an
exception. This is a fixed threshold, not currently configurable via `Settings`.

---

## 4. API Surface (summary)

All routes are mounted under `/api` except `/health` and static UI mounts. See
`app/models.py` for the full Pydantic request/response schemas.

| Method & Path              | Request                | Response               | Notes |
| --------------------------- | ----------------------- | ----------------------- | ----- |
| `GET /api/random-question`  | —                        | `{question_text, word_limit, year}` | 404 if the PYQ table is empty |
| `POST /api/evaluate`        | `EvaluateRequest`        | `EvaluateResponse`       | Runs the full 3-agent pipeline; 422 on validation/evaluator-contract failure, 502 on other LLM/network failure |
| `POST /api/model-answer`    | `ModelAnswerRequest`     | `ModelAnswerResponse`    | Retrieval + translation only; 422 if no PYQ match, 502 on translation failure |
| `GET /api/topics`           | —                        | `list[TopicResponse]`    | |
| `GET /api/attempts`         | —                        | `list[AttemptResponse]`  | Attempt history |
| `GET /health`               | —                        | `{status, service, version, database}` | Liveness/readiness probe target for the Dockerfile `HEALTHCHECK` |

---

## 5. Benchmark Metrics

`reports/EVALUATOR_CALIBRATION.md` (regenerated by `python scripts/calibrate_evaluator.py`)
reports:

| Metric | Value |
| --- | --- |
| Pearson correlation (r) | 0.9551 |
| Spearman rank correlation (ρ) | 0.9736 |
| Mean Absolute Error (MAE) | 0.5800 |

**These numbers were found in-repo and are reproducible in-repo** — but read what they
actually measure before citing them as "LLM evaluator accuracy," because they are not
that:

- `scripts/calibrate_evaluator.py::calibrate_answer_score()` is a **standalone,
  keyword/heuristic scoring function** (paragraph counts, presence of words like
  `"introduction"`/`"conclusion"`, counts of citation-like tokens such as `"article"`,
  `"commission"`, `"gst"`). It does **not** call `agents/evaluator.py::evaluate()` and
  does **not** make any LLM request. The actual LLM-based Evaluator Agent used in
  production is never exercised by this benchmark.
- The "expected" scores it correlates against (`8.8` for a synthetic "Tier A / Exemplar"
  answer, `6.0` for "Tier B / Adequate", `3.2` for "Tier C / Sub-par") are hardcoded
  constants chosen by the script's author, not human-graded ground truth, and the three
  synthetic answers themselves are template strings generated by the script
  (`scripts/calibrate_evaluator.py:150-178`), not real student submissions.
- So Pearson r / Spearman ρ / MAE above measure how well a hand-tuned keyword heuristic
  reproduces its own author-assigned tier labels on synthetic text it was implicitly
  tuned against — a self-consistency check of the heuristic proxy, not a validation of
  the LLM evaluator's real-world scoring reliability or agreement with human graders.
- The report's prose also has a **stale/inconsistent sample-size claim**: it hardcodes
  "40 UPSC ... PYQs" and "120 evaluation passes" in its template text
  (`scripts/calibrate_evaluator.py:229`), but `data/seed_data.json` currently contains 60
  PYQs across 5 topics, which the script's own loop would run through 3 tiers each = 180
  passes. The correlation/MAE numbers are computed live from whatever `seed_data.json`
  contains at run time, but the narrative counts in the report are a hardcoded string
  that was not updated when the seed set grew from 40 to 60 PYQs.

**Recommendation**: treat the numbers in `reports/EVALUATOR_CALIBRATION.md` as evidence
that the rubric weighting scheme and tier-separation logic are internally consistent, not
as a measured accuracy figure for the LLM Evaluator Agent in production. A real accuracy
benchmark would need to run `agents/evaluator.py::evaluate()` against a set of real
student answers with human-assigned reference scores.

No other source of Pearson/Spearman/MAE numbers was found in `README.md`,
`pitch_strategy.md`, or `notebooks/SuperKalamProject.ipynb`.

---

## 6. Known Failure Modes

| Failure | Where | Behavior | HTTP result |
| --- | --- | --- | --- |
| LLM call exceeds 60s | `evaluate()`, `generate_feedback()`, `translate_model_answer()` | `httpx.TimeoutException` raised, not caught locally | 502 (`evaluate.py` / `model_answer.py` generic `except Exception`) |
| Evaluator returns malformed JSON, retry also fails | `evaluate()` | `ValueError("...invalid JSON after retry...")` | 422 |
| Evaluator returns JSON missing a required key / rubric criterion / out-of-bounds score, retry also fails | `evaluate()` via `_validate_evaluation()` / `EvaluatorOutput` | `ValueError` / `pydantic.ValidationError` (subclass of `ValueError`) | 422 |
| Evaluator hits 429 on first attempt | `evaluate()` | Mock `[MOCK] ...429...` scores returned, pipeline continues | 200 (degraded content, not surfaced as an error) |
| Evaluator hits 429 on the *retry* attempt | `evaluate()` | Not special-cased — `raise_for_status()` raises `httpx.HTTPStatusError` | 502 |
| Feedback/translation call hits 429 or other non-2xx | `generate_feedback()` (no fallback) / `translate_model_answer()` (429 has a mock fallback; other errors do not) | `httpx.HTTPStatusError` unless 429 in `translate_model_answer` | 502 (except the 429/translate case, which is 200 with mock text) |
| Retrieval finds no PYQ above the 0.50 similarity floor (`/evaluate`) | `run_evaluate_pipeline` | Soft fallback: generic rubric + placeholder model answer; pipeline still runs | 200 |
| Retrieval finds no PYQ above the 0.50 similarity floor (`/model-answer`) | `run_model_answer_pipeline` | `ValueError(retrieval_result["error"])` raised | 422 |
| `OPENROUTER_API_KEY` not configured | `evaluate()`, `generate_feedback()`, `translate_model_answer()` | `ValueError` raised immediately, before any HTTP call | 422 |

---

## 7. Change Log (spec-relevant hardening)

- **Dockerfile**: `HEALTHCHECK` previously hardcoded `http://localhost:8080/health` while
  `CMD` listens on `${PORT:-8080}`; if `PORT` is overridden at runtime (as
  `docker-compose.yml` does — `PORT=8003`), the healthcheck silently probed the wrong
  port. Fixed to resolve `$PORT` (with the same `:-8080` default) at healthcheck-execution
  time via a shell substitution, so it can never drift from `CMD`.
- **`EvaluatorOutput` (`app/models.py`)**: added a Pydantic schema for the Evaluator
  Agent's parsed JSON (`scores: dict[str, float]`, `overall_score: float` bounded
  `[0, 10]`, `notes: str`, plus a field validator enforcing `0 <= score <= 10` for every
  entry in `scores`). `agents/evaluator.py::_validate_evaluation()` now validates against
  this model instead of hand-rolled dict/key checks; the per-request rubric-criteria
  subset check (which criteria must be present) remains a manual check afterwards since
  it depends on the caller-supplied rubric, not a fixed schema.
- **`requirements.txt`**: removed the unused `slowapi==0.1.9` dependency (see
  `docs/SPEC.md` deployment notes / hardening report for the rationale — it was never
  imported anywhere in the codebase and was not even installed in the environment this
  hardening pass was validated against).
