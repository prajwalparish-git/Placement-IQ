# Architecture

## 1. System overview
Everything runs in one Python process. Streamlit pages call the `piq` package. `piq` calls Groq over HTTPS (or `piq/mock.py` in MOCK_MODE) and reads and writes one SQLite file. There is no backend server, no queue and no vector store.

```
 Browser ──▶ Streamlit (app.py + views/) ──▶ piq.agents ──▶ piq.graph ──▶ piq.llm ──▶ Groq API | mock
                     │                           │                           │
                     └──── piq.db (sqlite3) ◀────┴────── agent_logs ◀────────┘
```

### The adaptive loop (data flow)
```
resume + role ─▶ Profile agent ─▶ StudentProfile ─(missing skills → topics)─┐
                                                                            ▼
quiz_attempts (last 3 per topic) ──────────────▶ weakness per topic (code) ─▶ Planner agent ─▶ WeeklyPlan (saved)
      ▲                                                                                    │
      └── student answers ◀── Quiz agent + critic ◀── difficulty from last score ◀─────────┘
Interview agent ⇄ student ─▶ Evaluator (rubric) ─▶ interview_turns ─▶ memory for the next session
```
Low quiz scores raise a topic's weakness. The next plan then has to give weak topics at least 50% of its minutes, and the critic enforces that. Week 2 shifts toward the topics the student scored badly on.

### Every generation step
```
START ─▶ generate ─▶ verify ──approved, or out of retries──▶ END
            ▲           │
            └──retry────┘   (the rejection reasons are added to the next prompt; MAX_CRITIC_RETRIES = 2)
```
`verify` runs the deterministic checks first, at no cost. Only quizzes then go on to an LLM critic call. Each attempt writes one `agent_logs` row with its approval result, retry count and reason.

## 2. Components
| Module | Responsibility |
|---|---|
| `app.py`, `views/*` | Pages, session state, button and chat handling. No business logic. |
| `piq/agents.py` | Builds prompts and `Task`s; turns LLM output into domain objects (e.g. readiness computed in code). |
| `piq/graph.py` | A single LangGraph (2 nodes and 1 conditional edge) that every agent reuses; streams step events. |
| `piq/llm.py` | The only LLM gateway: JSON mode, Pydantic validation, one repair retry, token and latency logging, mock switch. |
| `piq/checks.py` | Weakness scoring and the deterministic critic rules; question hashing for de-duplication. |
| `piq/db.py` + `schema.sql` | All persistence and aggregate queries. |
| `piq/formatter.py` | Output layer: models and rows to markdown and DataFrames. Pure functions. |
| `piq/ui.py` | Student selector; `run_agent` shows the critic loop live and keeps the log after reruns. |
| `piq/resume.py` | Extracts text from PDF, DOCX and TXT, with size and empty-text guards. |
| `scripts/seed.py`, `evaluation/run_eval.py` | Demo data; baseline-vs-system comparison. |

| Agent | Model | Output | Verified by |
|---|---|---|---|
| Profile | small | `ProfileExtraction` | skills not empty; `matched_skills` ⊆ the role's required list |
| Planner | large | `WeeklyPlan` | correct week number; days 1–7; every weak topic present and weak topics ≥ 50% of minutes |
| Quiz | large | `QuizSet` | topic, difficulty and count; 4 distinct options; no repeats (hash) → **LLM critic**: one defensible answer, on topic |
| Interviewer | large | `InterviewTurn` | one question; not asked before; follow-up/final flags set in code |
| Evaluator | large | `AnswerEvaluation` | schema only (each score an integer 0–5); overall computed in code |

## 3. How components communicate
- **Function calls.** Everything in-process is a plain synchronous Python call. We expose no REST API of our own.
- **External API.** Groq chat completions with `response_format=json_object`, through the `groq` SDK. HTTP 429 and transient errors retry inside the SDK (`max_retries=4`). A 404 on a model raises a clear "update `.env`" error.
- **Events.** `graph.run(..., on_event)` emits "generated", "critic rejected: reasons" and "approved". `ui.run_agent` shows them in an `st.status` box and saves them in session state.
- **DB calls.** `db.tx()` opens a short-lived connection per call with foreign keys on, committing or rolling back automatically. All queries use parameters.
- **LLM calls per user action** (typical / worst case, counting repair retries):

| Action | Calls |
|---|---|
| Onboard | 1 / 6 |
| Plan a week | 1 / 6 |
| Quiz (generate + critic) | 2 / 12 |
| Interview answer (evaluate + next question) | 2 / 8 |
| One evaluation case | about 7 |

## 4. Data model
```
students 1─* profiles        (profile_json, readiness_score)
students 1─* plans           (week_no, plan_json, rationale)   UNIQUE(student_id, week_no)
students 1─* quiz_attempts   (topic, difficulty, total, correct, score_pct)
quiz_attempts 1─* quiz_questions (question_hash, text, correct_index, chosen_index)
students 1─* interview_turns (session_id, type, question, answer, scores_json, overall)
agent_logs                   (agent, model, tokens, latency, critic_approved, retry_count, reject_reason)
```
- `students.usn` is the natural key (`NOT NULL UNIQUE`), and `id` is a UUID surrogate. Child rows are deleted with `ON DELETE CASCADE`.
- Storage rule: agent outputs that are always read whole are stored as JSON. Anything filtered, aggregated or charted gets its own column.
- Key queries:
  - `topic_performance`: a window function averages each topic's last 3 attempts.
  - `asked_questions`: feeds de-duplication.
  - `past_turns`: interview memory, replacing a vector store.
  - `agent_stats`: calls, latency, tokens and rejection rate per agent.

## 5. Key design decisions
1. **Minimal LangGraph.** One generate → verify → retry graph shared by every agent. The Supervisor/router node from the original plan was dropped because each page already knows its mode.
2. **Code computes, the LLM writes.** Readiness, missing skills, weakness, the weak-topic share, difficulty and the overall score are all deterministic. This makes them explainable, testable and stable from run to run.
3. **Two-stage critic.** Free deterministic checks run first. The paid LLM critic runs only for quizzes, and only once stage 1 passes. Rejection reasons are added to the retry prompt verbatim.
4. **SQLite history instead of ChromaDB and embeddings.** A student has dozens of turns, not millions, so recent rows fit in the prompt. This avoids torch, a model download and about 2 GB of dependencies.
5. **`sqlite3`, not SQLAlchemy.** Seven tables of hand-written SQL, with no extra dependency. The SQL is also easy to show in a DBMS review.
6. **The `groq` SDK directly.** No `langchain-groq` or `tenacity`: the SDK already provides JSON mode and backoff.
7. **Model IDs only in `.env`.** No startup fetch of the model list; a 404 fails loudly instead.
8. **MOCK_MODE is the default.** Mock output goes through the same validation and checks. The quiz's first mock attempt is deliberately flawed so the critic loop shows up offline.
9. **Streamlit's built-in charts** instead of Plotly; Altair already ships with Streamlit.
10. **Formatter as the output layer.** Views stay thin and every rendering decision can be unit-tested.
11. **Synchronous code only**, avoiding the known Streamlit-plus-asyncio problems.

### Complexity
- **Removed from the original plan:** ChromaDB and sentence-transformers, the Supervisor node, an LLM-computed readiness score, the live model-list fetch, SQLAlchemy alongside raw SQL, `langchain-groq`, `tenacity`, Plotly, a seven-package layout, and a prompt-hash cache (session state already prevents repeat calls).
- **Still optional:** LangGraph itself. The loop would be about 10 lines of plain Python. It stays because the scope was agreed and because it generates the report diagram (`scripts/export_graph.py`).

## 6. Known limitations
- No authentication: anyone using the app can select any student. This is out of scope.
- SQLite allows one writer at a time. That's fine for a lab demo, not for a whole batch using the app at once.
- Groq free-tier limits are shared across the organisation. A class using the app together will hit 429s; the SDK backs off and the UI waits.
- The critic is the same family of model as the generator, so their errors are correlated. Deterministic checks and manual labels (`questions.csv`) offset this.
- `matched_skills` is trusted after the subset check, so a resume containing injected instructions could inflate readiness.
- Resume text, which is personal data, is sent to a third-party API. Students need to consent.
- Weakness priors (0.7 for a resume gap, 0.4 otherwise) and the 50% share are heuristics that haven't been validated.
- No OCR, so scanned PDFs are rejected. No migrations. Timestamps are UTC.
- The evaluation has n = 20, which is small. Interview follow-up relevance is labelled by hand. Mock-mode results are invalid by design.

## 7. What would change at production scale
- **Storage:** Postgres with migrations; an ORM is worth adding at that point.
- **Access:** college SSO plus roles (student, coordinator) and per-student access control.
- **Architecture:** an API backend with a rate-limit-aware job queue for LLM calls; the frontend separated from the backend.
- **LLM:** a paid tier or provider fallback, response caching, and per-user quotas and cost tracking.
- **Content:** a vetted question bank, extended by the LLM, with a human review queue for flagged items.
- **Operations:** tracing and metrics instead of an `agent_logs` table; CI that runs lint, tests and the evaluation as a regression gate.
- **Retrieval:** embeddings only once per-student history outgrows the prompt budget.
- **Compliance:** data retention, encryption at rest, and a data processing agreement with the LLM provider.
