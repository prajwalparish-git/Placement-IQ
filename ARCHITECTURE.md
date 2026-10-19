# Architecture

## 1. System overview
Everything runs in one Python process. Streamlit pages call `piq.services`, the controllers. Services call the agents and the database. Agents reach Groq over HTTPS only through `piq.llm`, or `piq/mock.py` in MOCK_MODE. There is no separate backend server, no queue and no vector store.

```
 Browser ─▶ Streamlit views ─▶ piq.services ─▶ piq.agents ─▶ piq.graph ─▶ piq.llm ─▶ Groq API | mock
                                  │   (controllers)                        │
                                  └──────────▶ piq.db (sqlite3) ◀── agent_logs ┘
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
Low quiz scores raise a topic's weakness. The critic then enforces two rules on the next plan:
1. Weak topics together get at least 50% of the minutes.
2. Minutes never decrease as weakness increases: among scheduled topics, a weaker topic never gets fewer minutes than a less-weak one.

Live example: after a 20% OS quiz, OS went from 110 to 240 minutes and became the top topic.

### Every generation step
```
START ─▶ generate ─▶ verify ──approved, or out of retries──▶ END
            ▲           │
            └──retry────┘   generate(inputs, reasons, previous output); MAX_CRITIC_RETRIES = 2
```
`verify` runs the deterministic checks first, at no cost. Only quizzes then go on to an LLM critic call, and only for questions that haven't been judged yet. When every reason names a question, the retry regenerates **only those questions** and keeps the approved ones. Each attempt writes one `agent_logs` row with its approval result, retry count and reason.

## 2. Components
| Module | Responsibility |
|---|---|
| `app.py`, `views/*` | Pages and widgets only. They call `services`, `formatter` and `ui`. |
| `piq/services.py` | Controllers: onboard, plan, quiz, interview, dashboard. Validates input (`ServiceError`), runs agents, persists results, returns typed state (`InterviewSession`, `QuizResult`, `PlanOverview`). |
| `piq/agents.py` | Builds prompts and `Task`s; turns LLM output into domain objects (readiness computed in code); quiz critic with a verdict cache. |
| `piq/graph.py` | A single LangGraph (2 nodes and 1 conditional edge) that every agent reuses; streams step events. |
| `piq/llm.py` | The only LLM gateway: JSON mode, Pydantic validation, one repair retry, token and latency logging, `RateLimited` errors, mock switch. |
| `piq/checks.py` | Weakness scoring; deterministic plan, quiz, profile and turn rules; question hashing. |
| `piq/db.py` + `schema.sql` | All persistence and aggregate queries. |
| `piq/formatter.py` | Output layer: models and rows to markdown and DataFrames. Pure functions. |
| `piq/ui.py` | Student selector; `run_agent` shows the critic loop live and keeps the log, failures included, after reruns. |
| `piq/resume.py` | Extracts text from PDF, DOCX and TXT, with size and empty-text guards. |
| `scripts/*` | Demo seed, model and quota check, graph export, test-case report. |
| `evaluation/run_eval.py`, `report.py`, `views/results.py` | Baseline-vs-system comparison (resumable, checkpointed after every case), its report files, and the Results page. |

| Agent | Model | Output | Verified by |
|---|---|---|---|
| Profile | small | `ProfileExtraction` | skills not empty; `matched_skills` ⊆ the role's required list |
| Planner | large | `WeeklyPlan` | correct week number; days 1–7; weak topics present, together ≥ 50% of minutes; minutes ordered by weakness |
| Quiz | large | `QuizSet` | topic, difficulty and count; 4 distinct options; no repeats (hash) → **LLM critic** on unjudged questions: one defensible answer, on topic |
| Interviewer | large | `InterviewTurn` | one question; not asked before; follow-up/final flags set in code |
| Evaluator | large | `AnswerEvaluation` | schema only (each score an integer 0–5); overall computed in code |

## 3. How components communicate
- **Function calls.** Everything in-process is a plain synchronous Python call. The service functions are the API surface. We expose no HTTP routes, because Streamlit is the only client.
- **External API.** Groq chat completions with `response_format=json_object`, through the `groq` SDK. HTTP 429 and transient errors retry inside the SDK (`max_retries=4`).
  - A 429 that survives those retries becomes `RateLimited` with the server's retry-after hint. The UI shows it, and the evaluation stops early, keeping partial results.
  - A 404 on a model raises a clear "update `.env`" error.
  - Groq's `json_validate_failed`, an empty reply, is treated as repairable.
- **Events.** `graph.run(..., on_event)` emits "generated", "critic rejected: reasons" and "approved". `ui.run_agent` shows them in an `st.status` box and saves them in session state.
- **State.** Session state holds typed objects only (`QuizSet`, `QuizResult`, `InterviewSession`). All durable state is in SQLite.
- **DB calls.** `db.tx()` opens a short-lived connection per call with foreign keys on, committing or rolling back automatically. All queries use parameters.

## 4. Models and measured cost
| Role | Model | Why |
|---|---|---|
| Large: planner, quiz, critic, interviewer, evaluator | `openai/gpt-oss-120b` | Strictest critic in a probe of every chat model Groq serves; it caught real multi-answer questions. It also produced the best plans and evaluations. |
| Small: profile extraction | `openai/gpt-oss-20b` | Fastest correct extraction, about 2 s. Quotas are per model, so it keeps profile calls out of the large model's token budget. |

Free-tier limits, read from the response headers: **8,000 tokens/minute and 1,000 requests/day per model.** Typical cost measured live:

| Action | LLM calls | Time |
|---|---|---|
| Onboard | 1 | ~2.5 s |
| Plan a week | 1 (2 if Groq returns empty JSON) | 5–20 s |
| Quiz (generate + critic) | 2–4 | 7–17 s |
| Interview answer (evaluate + next question) | 2 | 2–18 s |
| One evaluation case | about 7 | 1–2 min, limited by tokens/minute |

## 5. Evaluation
`python -m evaluation.run_eval` compares a single-prompt baseline with PlacementIQ on 20 frozen cases. Both are judged by the same deterministic checks and the same LLM critic.

| Metric | Measured how |
|---|---|
| Plan valid rate, weak-topic share | `check_plan` on each system's plan |
| Quiz valid rate, duplicates vs history | `check_quiz` + critic on each system's quiz |
| Duplicate rate over N quizzes (`--consecutive N`) | N back-to-back quizzes per topic; baseline without memory |
| Interview follow-up relevance (`--interviews`) | after a deliberately vague answer, a judge (small model) checks the next question |
| Cost per agent | `agent_logs` in the evaluation's own `eval.db` |

The run saves its state after every case, so a run cut short by the daily quota or killed continues with `--resume`. `evaluation/report.py` turns the summary into `report.md` and an SVG chart. The Results page shows the same data.

## 6. Data model
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

## 7. Key design decisions
1. **Minimal LangGraph.** One generate → verify → retry graph shared by every agent. The Supervisor/router node from the original plan was dropped because each page already knows its mode.
2. **Service layer instead of HTTP routes.** Controllers are plain functions with typed results. Every user flow is integration-tested without Streamlit. A REST wrapper would be one thin file if a second client ever appears.
3. **Code computes, the LLM writes.** Readiness, missing skills, weakness, weak-topic share, minute ordering, difficulty and the overall score are all deterministic. This makes them explainable, testable and stable from run to run.
4. **Two-stage critic with per-question repair.** Free deterministic checks run first. The LLM critic judges each question once: verdicts are cached by exact content. A retry replaces only the rejected questions. This was found live: regenerating all five questions on each retry never converged (3 of 3 attempts rejected). Per-question repair passes on attempt 2.
5. **SQLite history instead of ChromaDB and embeddings.** A student has dozens of turns, not millions, so recent rows fit in the prompt. This avoids torch, a model download and about 2 GB of dependencies.
6. **`sqlite3`, not SQLAlchemy.** Seven tables of hand-written SQL, with no extra dependency. The SQL is also easy to show in a DBMS review.
7. **The `groq` SDK directly.** No `langchain-groq` or `tenacity`: the SDK already provides JSON mode and backoff.
8. **Model IDs only in `.env`.** `scripts/check_models.py` verifies them before a demo, and a 404 at runtime fails loudly.
9. **MOCK_MODE is the default.** Mock output goes through the same validation and checks. The quiz's first mock attempt is deliberately flawed so the critic loop shows up offline.
10. **Streamlit's built-in charts** instead of Plotly; Altair already ships with Streamlit.
11. **Formatter as the output layer.** Views stay thin and every rendering decision can be unit-tested.
12. **Synchronous code only**, avoiding the known Streamlit-plus-asyncio problems.

### Complexity
- **Removed from the original plan:** ChromaDB and sentence-transformers, the Supervisor node, an LLM-computed readiness score, the live model-list fetch at startup, SQLAlchemy alongside raw SQL, `langchain-groq`, `tenacity`, Plotly, a seven-package layout, and a prompt-hash cache (session state already prevents repeat calls).
- **Still optional:** LangGraph itself. The loop would be about 10 lines of plain Python. It stays because the scope was agreed and because it generates the report diagram (`scripts/export_graph.py`).

## 8. Known limitations
- No authentication: anyone using the app can select any student. This is out of scope.
- SQLite allows one writer at a time. That's fine for a lab demo, not for a whole batch using the app at once.
- 8,000 tokens/minute per model allows roughly two quiz generations a minute. A class using the app together will hit 429s; the SDK backs off and then the UI says how long to wait.
- The critic is the same model as the generator, so their errors are correlated. Deterministic checks and manual labels (`questions.csv`) offset this.
- gpt-oss models spend hidden reasoning tokens, which count toward the quota, and call latency varies from 1 to 20 s.
- `matched_skills` is trusted after the subset check, so a resume containing injected instructions could inflate readiness.
- Resume text, which is personal data, is sent to a third-party API. Students need to consent.
- Weakness priors (0.7 for a resume gap, 0.4 otherwise) and the 50% share are heuristics that haven't been validated.
- The verdict cache lives in memory per process, so it is lost on restart.
- No OCR, so scanned PDFs are rejected. No migrations. Timestamps are UTC.
- On Streamlit Community Cloud the disk resets on restart; `SEED_DEMO=true` recreates the demo student, but other data is lost.
- The evaluation has n = 20, which is small. Interview follow-up relevance is labelled by hand. Mock-mode results are invalid by design.

## 9. What would change at production scale
- **Storage:** Postgres with migrations; an ORM is worth adding at that point.
- **Access:** college SSO plus roles (student, coordinator) and per-student access control.
- **Architecture:** an HTTP API over `services` with a rate-limit-aware job queue for LLM calls; the frontend separated from the backend.
- **LLM:** a paid tier or provider fallback, a critic from a different model family, a shared verdict cache, and per-user quotas and cost tracking.
- **Content:** a vetted question bank, extended by the LLM, with a human review queue for flagged items.
- **Operations:** tracing and metrics instead of an `agent_logs` table; CI already runs format, lint and tests, and should also run the evaluation as a regression gate.
- **Retrieval:** embeddings only once per-student history outgrows the prompt budget.
- **Compliance:** data retention, encryption at rest, and a data processing agreement with the LLM provider.
