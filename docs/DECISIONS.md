# Architecture Decisions — SuperKalam

> Lightweight architecture decision records (ADRs). The system specification is in [SPEC.md](./SPEC.md).

Rationale here is taken only from commit messages, code comments and the code itself. Where no reason was recorded, the entry says so.

---

## ADR-01: Groq-hosted `openai/gpt-oss-120b` as the default LLM

**Context:** The evaluator and feedback agents call an OpenAI-compatible chat-completions endpoint. The previous default, `llama-3.3-70b-versatile`, was retired from Groq's catalog, and `/api/evaluate` returned "404 Not Found" from Groq even with a valid key.
**Decision:** Default `OPENROUTER_MODEL` to `openai/gpt-oss-120b` and `OPENROUTER_BASE_URL` to `https://api.groq.com/openai/v1/chat/completions`. Send `"reasoning_effort": "low"` on all three LLM calls, because the model reasons before answering and can spend the whole `max_tokens` budget on hidden reasoning, which truncated the JSON output (`finish_reason: "length"`).
**Alternatives rejected:** None recorded.
**Consequences:** The setting and key are still named `OPENROUTER_API_KEY` / `OPENROUTER_MODEL`, although the default endpoint is Groq. `deploy.yml` passes `secrets.GROQ_API_KEY || secrets.OPENROUTER_API_KEY` as `OPENROUTER_API_KEY`. Groq retires models periodically (the setting's description says it last broke this default in Sep 2026), and `docker-compose.yml` still defaults to the retired llama model.
**Evidence:** commit `db271f3`; `configs/settings.py:41-52`; `agents/evaluator.py:104-106`; `.github/workflows/deploy.yml:52`.

---

## ADR-02: Pydantic validation of the evaluator's JSON output

**Context:** The evaluator LLM must return strict JSON. Hand-rolled dict checks were the only guard on the parsed output.
**Decision:** Validate the parsed output with the `EvaluatorOutput` Pydantic model (`scores`, `overall_score` bounded 0-10, `notes`, each score 0-10). The check that every criterion of the active rubric is present stays manual, because the required set depends on the per-topic rubric. Markdown fences are stripped before parsing, and the call is retried once with a stricter prompt.
**Alternatives rejected:** None recorded.
**Consequences:** A response that fails validation twice surfaces as HTTP 422 from the raw `JSONDecodeError` / `ValueError` of the retry (not the "after retry" message, which only the `retry=False` path raises). The 429 mock result skips this validation.
**Evidence:** commit `c5ff69d`; `app/models.py:54-90`; `agents/evaluator.py:144-176`, `agents/evaluator.py:179-206`.

---

## ADR-03: Mock scores on HTTP 429 instead of failing the request

**Context:** The free or shared LLM tier can rate-limit. The commit that added the fallback describes it as "API rate-limiting fallbacks" so the application can proceed.
**Decision:** On the first evaluator call, a 429 returns a mock evaluation (every rubric criterion 6, overall 6.0, notes prefixed `[MOCK] API Rate Limit Exceeded (429)`). `translate_model_answer` returns a `[MOCK]` text on 429. This is a per-request fallback, not a circuit breaker: nothing tracks failures or opens or closes a breaker.
**Alternatives rejected:** None recorded.
**Consequences:** A rate-limited request returns HTTP 200 with fake scores that are saved as an `Attempt`. The retry call, `generate_feedback()` and other non-2xx responses have no such fallback and return HTTP 502.
**Evidence:** commit `2f5144c`; `agents/evaluator.py:122-127`; `agents/feedback.py:142-143`; `docs/SPEC.md` section 3.3.

---

## ADR-04: Calibration benchmark as a standalone heuristic

**Context:** The project needed a reproducible calibration check for rubric scoring without LLM calls.
**Decision:** `scripts/calibrate_evaluator.py` scores synthetic tier answers with a keyword/paragraph heuristic and correlates them with author-assigned tier labels (8.8 / 6.0 / 3.2). It does not call the LLM evaluator. The report carries a methodology disclaimer, and `docs/SPEC.md` section 5 explains what the numbers do and do not show.
**Alternatives rejected:** None recorded.
**Consequences:** Pearson 0.9551, Spearman 0.9736 and MAE 0.58 measure self-consistency of the heuristic, not LLM accuracy against human graders. The report's header text ("40 PYQs", "120 passes") is stale against 60 seeded PYQs, and its B-vs-C margin of +1.99 is marked as passing a 2.0 target.
**Evidence:** commit `58c2f42` (script and report), `c5ff69d` (disclaimer); `reports/EVALUATOR_CALIBRATION.md`.

---

## ADR-05: Dense-only ChromaDB retrieval with a 0.50 similarity floor

**Context:** A student's question is matched to a known PYQ to find its model answer and rubric.
**Decision:** Embed with `all-MiniLM-L6-v2` into a persistent ChromaDB collection with cosine distance, take the top 1 and reject similarity below 0.50. For `/api/evaluate` a miss falls back to a generic rubric and placeholder model answer; for `/api/model-answer` it raises a 422.
**Alternatives rejected:** None recorded. There is no lexical component.
**Consequences:** Questions that hinge on exact identifiers can be mis-matched (see `docs/SPEC.md` section 2.1). The threshold is fixed in code, not a setting.
**Evidence:** `agents/retrieval.py:60`; `configs/settings.py` (`EMBEDDING_MODEL`, `CHROMA_COLLECTION`).
