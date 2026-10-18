# CLAUDE.md

## Purpose
PlacementIQ is a placement-readiness coach for engineering students. Agents profile a resume, plan the week, set quizzes and run mock interviews. A critic checks every generated output. Quiz results change the next week's plan.

College mini-project scope: one Streamlit process and one SQLite file. Keep it that small.

## Tech stack (pinned in `requirements*.txt`)
| Layer | Choice | Version |
|---|---|---|
| Language | Python | 3.13 (tested on 3.13.3) |
| UI and charts | Streamlit (includes Altair and pandas) | 1.66.0 |
| Agent loop | LangGraph | 1.2.16 |
| LLM | Groq SDK, JSON mode, built-in retry on 429 | 1.7.0 |
| Validation | Pydantic | 2.14.1 |
| Storage | SQLite via stdlib `sqlite3` | stdlib |
| Resume parsing | pypdf / python-docx | 6.21.1 / 1.2.0 |
| Config | python-dotenv | 1.2.4 |
| Dev | pytest / ruff | 9.1.1 / 0.17.1 |

## Directory structure
```
app.py              Entry point: settings check, DB init, sidebar student picker, page navigation
views/              One file per page. Keep them thin: call piq/, render through formatter
  onboard.py        Resume (upload or sample) -> Profile agent -> save student and profile
  plan.py           Weakness table, generate next week's plan, week-vs-week minutes chart
  quiz.py           Suggested difficulty, generate quiz (critic loop), take it, review
  interview.py      Chat mock interview with per-answer rubric feedback
  dashboard.py      Score trends, plan minutes, agent_logs stats and rejections
piq/                Application package. Only ui.py imports Streamlit
  config.py         Env settings (cached) and constants: topics, thresholds, sizes
  schemas.py        Pydantic models for every LLM output and derived objects
  llm.py            The ONLY LLM gateway: JSON mode, validation, one repair retry, agent_logs, mock
  mock.py           Deterministic MOCK_MODE responses (must pass the same checks)
  prompts.py        Every system prompt
  graph.py          LangGraph loop: generate -> verify -> retry | done
  agents.py         Profile, Planner, Quiz (+ LLM critic), Interviewer, answer Evaluator
  checks.py         Deterministic rules: weakness score, critic checks, question hashing
  db.py             All SQL. One short-lived connection per call
  schema.sql        DDL (CREATE IF NOT EXISTS; there are no migrations)
  resume.py         PDF/DOCX/TXT -> text (no OCR)
  formatter.py      Output layer: models/rows -> markdown and DataFrames (pure, testable)
  ui.py             Streamlit helpers: student selector, live and persisted agent step log
data/
  role_skills.json  Role -> required skill -> syllabus topic (drives readiness and weakness)
  sample_resumes/   Three fictional resumes (TXT)
  placementiq.db    Runtime database (git-ignored; created on first run)
evaluation/
  test_cases.json   20 frozen cases (5 roles x 4 score profiles)
  run_eval.py       Baseline (one prompt) vs PlacementIQ; writes results/
scripts/
  seed.py           Demo student DEMO0001 with 4 weeks of history (no LLM calls)
  export_graph.py   Mermaid diagram of the compiled graph -> docs/
docs/critic_graph.mmd  Generated graph diagram for the report
tests/              pytest, fully offline (MOCK_MODE + temp DB), includes headless UI tests
```

## Commands
Run from the repo root. On Windows, activate with `.venv\Scripts\activate`.
```
python -m venv .venv
pip install -r requirements-dev.txt     # runtime + pytest + ruff
copy .env.example .env                  # optional; without .env the app runs in MOCK_MODE
python -m scripts.seed                  # demo student with 4 weeks of history
streamlit run app.py                    # dev server, http://localhost:8501
pytest                                  # all tests, offline, about 30 s
ruff format . ; ruff check .            # format + lint (must be clean)
python -m evaluation.run_eval           # live comparison; needs MOCK_MODE=false and quota
python -m scripts.export_graph          # refresh docs/critic_graph.mmd
```
There is no build step. Live mode needs `GROQ_API_KEY`, `GROQ_MODEL_LARGE` and `GROQ_MODEL_SMALL` set and `MOCK_MODE=false` in `.env`.

## Coding conventions
- Format and lint with ruff (`pyproject.toml`: line length 100, py313, rules E F W I B UP SIM). Leave no lint errors.
- Type hints on every function signature. Use PEP 695 generics (`def f[T](...)`), not `TypeVar`.
- Every LLM output is a Pydantic model returned by `piq.llm.call`. Never parse prose, and never call the Groq SDK from anywhere else.
- If code can compute something, code computes it: readiness, missing skills, weakness, weak-topic share, difficulty, overall score, turn bookkeeping. The LLM only does what needs language.
- New generation tasks are a `graph.Task(name, generate, verify)` run through `graph.run` / `run_or_raise`. `verify` returns reasons as text, and those reasons are fed back into the retry prompt.
- Put cheap deterministic checks in `checks.py` and run them before any LLM critic call.
- All SQL lives in `piq/db.py` and uses `?` parameters. Never build SQL with f-strings. Agents never write domain tables; callers do.
- Prompts live only in `piq/prompts.py`. Constants and thresholds live only in `piq/config.py`.
- Views stay thin: no business logic, and rendering goes through `formatter.py`.
- Code is synchronous only (no asyncio), because of Streamlit.
- Each module starts with a docstring stating its job; add comments only for non-obvious reasons.
- Every change ships with a test. Tests must pass offline in MOCK_MODE. Any new mock response must pass the same schema and checks as real output.
- Tests never read the real `.env`: `tests/conftest.py` points `PIQ_DOTENV` at a missing file and gives each test a fresh database. Live code paths are tested with the fake Groq client in `tests/test_llm.py`.
- A new dependency needs a one-line justification in `requirements.txt` and an exact version pin. The default answer is no.

## Constraints and do-not-touch
- `PlacementIQ_Project_Spec.md` is a local planning file. It is git-ignored and must never be staged, committed or copied into docs.
- `.env` must never be committed or printed.
- **Never put model IDs in code.** They come only from `.env`, because Groq renames and retires models.
- `evaluation/test_cases.json` is frozen. Editing it invalidates all earlier results.
- `data/role_skills.json` changes readiness and weakness for every student. Edit it only on purpose, and keep its topics within `Aptitude, DBMS, OS, CN, DSA, OOP` (a test enforces this).
- The `scripts/seed.py` trajectory (OS and DBMS start weak) is what the demo depends on. Do not change it casually.
- `students.usn` is required (`NOT NULL UNIQUE`). Never drop it or make it optional.
- `schema.sql` has no migrations. After a schema change, delete `data/placementiq.db` and reseed.
- Groq's free tier is the only external service. Stay within its limits: batch questions into one call, use the small model for extraction, and keep MOCK_MODE as the default.
- Out of scope: auth, voice/video, a code judge, scraping, a vector database or embeddings, async, a separate backend.
