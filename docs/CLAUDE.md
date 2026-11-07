# CLAUDE.md

## Purpose
PlacementIQ is a placement-readiness coach for engineering students. Agents profile a resume, plan the week, set quizzes and run mock interviews. A critic checks every generated output. Quiz results change the next week's plan.

College mini-project scope: one Streamlit process and one SQLite file for the app. Keep it that
small. The separate telemetry layer (`database/`) may use PostgreSQL and falls back to its own
SQLite file; the six-step journey records every activity there and the faculty dashboard
reads it back (through `piq/journey.py`).

## Tech stack (pinned in `requirements*.txt`)
| Layer | Choice | Version |
|---|---|---|
| Language | Python | 3.13 (tested on 3.13.3) |
| UI and charts | Streamlit (includes Altair and pandas; both pinned because imported directly) | 1.66.0 (Altair 6.3.0, pandas 3.0.6) |
| Agent loop | LangGraph | 1.2.16 |
| LLM providers (`core/ai_router.py`) | Gemini REST (primary), Groq SDK, local Ollama REST; JSON mode each | Groq 1.7.0, httpx 0.28.1 |
| Voice (`core/speech_router.py`) | ElevenLabs REST, else the browser's Web Speech API | httpx 0.28.1 |
| LLM models (`.env`) | `openai/gpt-oss-120b` (large), `openai/gpt-oss-20b` (small) | verified 2026-10-19 |
| Validation | Pydantic | 2.14.1 |
| Storage | SQLite via stdlib `sqlite3` | stdlib |
| Telemetry storage (`database/`) | SQLAlchemy 2 + psycopg 3 (PostgreSQL, SQLite fallback) | 2.1.6 / 3.3.6 |
| Resume parsing | pypdf / python-docx | 6.21.1 / 1.2.0 |
| Config | python-dotenv | 1.2.4 |
| Dev | pytest / ruff | 9.1.1 / 0.17.1 |
| Dev, visual QA and docs only | Playwright (+ Chromium) / Pillow | 1.64.0 / 12.3.0 |

Playwright drives `scripts/screenshots.py` and prints `scripts/summary_pdf.py` (never CI or
tests); Pillow compresses its PNGs and is the version Streamlit already installs.

## Directory structure
```
app.py              Entry point: theme CSS, logo, settings check, DB init, sidebar, navigation (the six
                    numbered journey steps, then More tools), last-resort guard: a crashed page
                    shows a message, never a traceback (PIQ_RAISE_ERRORS=1 re-raises, for tests)
server.py           FastAPI over piq.services for the Next.js app: catalog, instant quizzes, plan,
                    dashboard, interview turns (server-sent events), resume ATS/PDF/bullet polish
frontend/          Next.js 14 (App Router) + Tailwind + lucide-react: /, /resume-builder, /quiz,
                    /interview, /plan, /dashboard. Talks only to server.py (NEXT_PUBLIC_API_URL)
views/              One file per page. Calls piq.services, piq.formatter, piq.charts and piq.ui
  Placement journey (steps 1-6; steps 2-5 run the agents/ package through piq/journey.py):
  onboard.py        1. Resume (upload or sample) -> profile; taken-USN confirmation; delete student
  scanner.py        2. Resume scan against any catalog role: found and missing skills, degree, stream
  roadmap.py        3. 7-day roadmap for the gaps, saved week by week; tasks ticked off and kept
  critic_quiz.py    4. Critic-checked MCQs on one skill (question bank fallback), graded, recorded
  voice_interview.py 5. Spoken scenario question (ElevenLabs or browser voice), spoken/typed answer,
                    0-15 rubric with proctor flags, recorded
  faculty.py        6. Cohort by stream, score spreads, rubric criteria, skill gaps, weekly trend,
                    Layer 3 service health, readiness report as CSV
  More tools:
  home.py           Default page: the loop explained, or readiness, streak and today's focus
  plan.py           Week pills, day-by-day plan with check-off and export, shift and weakness charts
  quiz.py           Several topics x 1-50 questions (100 max), difficulty-mix slider, batched
                    critic trail, blank guard, breakdown by topic/difficulty/level, mistakes
  resume_builder.py Own details only -> ATS resume + PDF; versions, diff, domain lock, advice
  projects.py       Project space (computing domains): repositories, README, work log, calendar
  interview.py      Chat mock interview, scored feedback, retry for a failed follow-up, summary
  dashboard.py      Readiness, streak, topic mastery, plans, interviews; agents and critic apart
  results.py        Evaluation scorecard: advanced parameters rated 0-10 (piq/scorecard.py)
core/               Layer 3: self-healing routers. Never import Streamlit
  ai_router.py      Gemini -> Groq -> Ollama, a circuit breaker each, Ollama health check; raises
                    AllProvidersDown when none answers (piq/llm.py then serves the offline tier)
  speech_router.py  ElevenLabs -> browser Web Speech API (no pyttsx3: it speaks on the server)
piq/                Application package. Only ui.py imports Streamlit
  services.py       Controllers: every user operation; validates, runs agents, persists, typed state
  journey.py        Controllers for journey steps 2-6: run agents/, record telemetry (best-effort:
                    a failed write is reported as saved=False, never raised), read the cohort
  cohort.py         Pure cohort analytics: readiness per student and band, stream summaries, chart
                    inputs, the readiness report CSV (formula-injection safe)
  config.py         Env settings (cached) and constants: CS core topics, thresholds, sizes
  syllabus.py       Domain topics, role focus topics, topic colour slots (career_catalog.json)
  degrees.py        Qualifications (degrees.json) and the catalog roles a degree qualifies for
  question_bank.py  Local MCQ bank -> syllabus topics (bank_topics.json); a share of each quiz
  scorecard.py      Evaluation parameters from summary.json + CSVs, scores and ratings (pure)
  resume_builder.py Resume data, ATS audit, version diff, Latin-1-safe PDF (fpdf2)
  schemas.py        Pydantic models for every LLM output and derived objects
  llm.py            The ONLY LLM gateway: messages, validation, repair retry, agent_logs, mock and
                    the offline tier; transport is core/ai_router.py
  mock.py           Deterministic MOCK_MODE responses (must pass the same checks)
  prompts.py        Every system prompt
  graph.py          LangGraph loop: generate -> verify -> retry | done
  agents.py         Profile, Planner, Quiz (+ LLM critic, verdict cache), Interviewer, Evaluator
  checks.py         Deterministic rules: weakness score, critic checks, question hashing
  db.py             All SQL. One short-lived connection per call
  schema.sql        DDL (CREATE IF NOT EXISTS; there are no migrations)
  resume.py         PDF/DOCX/TXT -> text (no OCR)
  formatter.py      Output layer: models/rows -> markdown, escaped HTML, DataFrames, files (pure)
  charts.py         Altair chart builders (pure, tested) + cached Vega-Lite specs for the views
  ui.py             Streamlit helpers: student selector, critic trail, design-system components
database/           Telemetry layer (SQLAlchemy). Only piq/journey.py imports it
  connection.py     DatabaseManager: PostgreSQL (DATABASE_URL) or SQLite fallback; failover log
  models.py         StudentProfile, ResumeAnalysis, StudyPlan, QuizAttempt, VoiceInterviewSession
  crud.py           Save/fetch per table, a student's whole history, aggregated analytics
static/             Served at app/static: app.css, brand/ (mark, wordmark), fonts/ (OFL woff2)
data/interview_tracks.json  Five interview tracks per domain, plus tracks a degree adds (BCA/MCA/MSc/MSE)
data/
  career_catalog.json Domains: stream, ordered topics (<= 10), core topics, code_space, roles
                    (commerce, law and management roles also list tools and benchmarks)
  role_skills.json  Role -> required skill -> its domain's topic (drives readiness and weakness);
                    "aliases": other names a resume may use for a skill
  degrees.json      Class 10 to doctorate: code, level, field; groups roles' eligibility uses;
                    streams (Engineering, Commerce, Law, Management): degrees, specialisations, domains
  bank_topics.json  Question-bank topic -> the syllabus topic it serves (or null)
  questions/        mcq_bank.csv: the question bank (committed; the raw MCQ.csv source is not).
                    Columns: stream, domain, role (as the catalog names them), topic, difficulty,
                    question, option_a-d, correct_option, explanation, bloom_level
  sample_resumes/   Six fictional resumes (TXT): three CS, one each for commerce, law, management
  placementiq.db    Runtime database (git-ignored; created on first run)
  placement_nexus.db  Telemetry fallback (git-ignored; used when DATABASE_URL is unset or down)
evaluation/
  test_cases.json   20 frozen cases (5 roles x 4 score profiles)
  run_eval.py       Baseline (one prompt) vs PlacementIQ; resumable, checkpointed; writes results/
  report.py         results/summary.json -> report.md (tables) + chart.svg for the report
scripts/
  seed.py           Demo student DEMO0001 with 4 weeks of history (no LLM calls)
  seed_cohort.py    Fictional cohort (COHORT001..) across four streams for the faculty dashboard;
                    --replace removes the earlier one. SEED_DEMO=true seeds both on start
  check_models.py   Are the configured Groq models served, JSON-capable, and within quota?
  export_graph.py   Mermaid of the compiled graph -> docs/critic_graph.mmd + .md
  test_report.py    Runs pytest and writes docs/test_report.md (test-case table)
  screenshots.py    Dev: every page and flow via Playwright, 3 widths x 2 schemes; fails on console errors
  perf.py           Dev: render time and queries per page via AppTest (--mode fresh | rerun)
  tunnel.ps1 / .bat Demo: the app on a temporary public URL (Cloudflare quick tunnel; Windows)
  summary_pdf.py    Docs: results/summary.json -> docs/PlacementIQ_Summary.pdf (Playwright)
docs/               diagrams.md (use case, DFD, ER, sequence), critic graph, test report, performance.md,
                    PlacementIQ_Summary.pdf (abstract, key features, problems it solves)
  design/           DESIGN.md (the design system), curated before/ and after/ screenshots, perf tables
.github/workflows/  ci.yml: format check, lint and tests on push to main and on PRs (read-only token)
.streamlit/         config.toml: theme (light/dark tokens, fonts), static serving, 5 MB uploads, no telemetry
tests/              pytest, fully offline: one file per layer, services integration, headless UI
```

## Commands
Run from the repo root. On Windows, activate with `.venv\Scripts\activate`.
```
python -m venv .venv
pip install -r requirements-dev.txt     # runtime + pytest + ruff
copy .env.example .env                  # then add GROQ_API_KEY; without .env the app runs in MOCK_MODE
python -m scripts.check_models          # before a demo: models served, JSON mode, quota left
python -m scripts.seed                  # demo student with 4 weeks of history
python -m scripts.seed_cohort           # demo cohort for the faculty dashboard
streamlit run app.py                    # dev server, http://localhost:8501
uvicorn server:app --port 8000          # API for the Next.js frontend
cd frontend ; npm install ; npm run dev # Next.js on http://localhost:3000 (npm run build to check types)
pytest                                  # all tests, offline, about 2 min
ruff format . ; ruff check .            # format + lint (must be clean)
python -m evaluation.run_eval --consecutive 5 --interviews   # live; ~360k tokens = 2 days of quota
python -m evaluation.run_eval --consecutive 5 --interviews --resume   # continue (same flags)
python -m evaluation.report             # results/report.md + chart.svg
python -m scripts.summary_pdf           # docs/PlacementIQ_Summary.pdf with the latest numbers
python -m scripts.test_report           # docs/test_report.md from a real test run
python -m scripts.export_graph          # refresh docs/critic_graph.mmd and .md
python -m scripts.screenshots docs/design/after [--pages quiz] [--widths 1440,390]   # visual review
python -m scripts.perf docs/design/perf.md [--mode rerun]   # render time per page
```
There is no build step. `.env.example` already contains the verified model IDs. Live mode needs `GROQ_API_KEY` and `MOCK_MODE=false`.

## Coding conventions
- Format and lint with ruff (`pyproject.toml`: line length 100, py313, rules E F W I B UP SIM). Leave no lint errors.
- Type hints on every function signature. Use PEP 695 generics (`def f[T](...)`), not `TypeVar`.
- Layering: `views -> services -> agents -> graph -> llm`, with `db` used by `services` and `llm`. Views never import `agents`, `core`, `database` or `db`; the journey pages go through `piq.journey`.
- `services` validate every input and raise `ServiceError` with a message safe to show users. They return typed state, for example `InterviewSession`, `QuizResult` and `PlanOverview`.
- Every LLM output is a Pydantic model returned by `piq.llm.call`. Never parse prose, and never call a provider from anywhere else: transport lives only in `core/ai_router.py` (exceptions: `scripts/check_models.py`, and Whisper transcription in `agents/rubric_evaluator_agent.py`).
- **The UI never crashes on an AI or voice outage.** A provider that fails is paused by its breaker and the next one answers; with none left, `piq/llm.py` serves the deterministic offline tier (`piq/mock.py`) unless `AI_OFFLINE_FALLBACK=false`, and the `agents/` package falls back to its own banks. The evaluation always sets it false: an offline answer is not the model's.
- If code can compute something, code computes it: readiness, missing skills, weakness, weak-topic share, minute ordering, difficulty, overall score, turn bookkeeping. The LLM only does what needs language.
- New generation tasks are a `graph.Task(name, generate, verify)` run through `graph.run` / `run_or_raise`. `generate(inputs, reasons, previous)` receives the rejection reasons and the rejected output. `verify` returns reasons as text.
- Problems with a single quiz question must be built with `checks.question_reason(i, msg)`. Then only that question is regenerated.
- Put cheap deterministic checks in `checks.py` and run them before any LLM critic call.
- All SQL lives in `piq/db.py` and uses `?` parameters. Never build SQL with f-strings. Agents never write domain tables; services do. The one exception is the telemetry layer: `database/crud.py` queries through SQLAlchemy (no raw SQL strings), so one code path serves PostgreSQL and SQLite.
- Prompts live only in `piq/prompts.py`. Constants and thresholds live only in `piq/config.py`.
- Views stay thin: no business logic, and rendering goes through `formatter.py` and `charts.py`.
- **Theme first, CSS last.** Colours, fonts and radii live in `.streamlit/config.toml` (light and dark), mirrored by `config.PALETTE`, `SEMANTIC_COLORS` and `TOPIC_COLORS`; `tests/test_theme.py` checks contrast and that both agree. `static/app.css` (under 150 lines and 8 KB) holds only what the theme cannot express: every selector includes a `data-testid` (own classes only beneath one, never `.st-emotion-cache-*`), every colour is a `PALETTE` token written `light-dark(light, dark)`, and each rule says why it exists.
- **Topic colours mean topics.** A domain's n-th topic takes the n-th colour of `TOPIC_PALETTE` (charts get it from the theme's categorical palette through `syllabus.color_domain`; chips through `syllabus.color_slot`). Never use them for status; every status shows an icon and words, never colour alone.
- **Escape every dynamic value.** Resume, LLM and user text go through `formatter.md_escape` in Markdown and `html.escape` in HTML builders (`st.html`); tests feed `<script>`, `*p`, `__init__` and image Markdown through each builder.
- **Charts** are pure builders in `charts.py` returning `alt.Chart` (tests check encodings); views render the matching `*_spec` (plain Vega-Lite cached per distinct data) with `st.vega_lite_chart`. Titles state the takeaway as text above the chart; every mark has a tooltip.
- Icons are Material Symbols (`:material/name:`), never emoji. Copy is sentence case, British spelling, no exclamation marks.
- **Screenshot review loop** for any page change: `python -m scripts.screenshots docs/design/after --pages <page>`, open the PNGs at every width and in both schemes, fix, capture again. Zero browser console errors.
- Code is synchronous only (no asyncio), because of Streamlit.
- Each module starts with a docstring stating its job; add comments only for non-obvious reasons.
- Every change ships with a test. Tests must pass offline in MOCK_MODE. Any new mock response must pass the same schema and checks as real output.
- Tests never read the real `.env`: `tests/conftest.py` points `PIQ_DOTENV` at a missing file, clears caches and gives each test a fresh database. Live code paths are tested with fake Groq clients (`tests/test_llm.py`, `tests/test_check_models.py`).
- Commits follow Conventional Commits (`feat(scope): …`, `fix(scope): …`), one logical unit per commit, and every commit passes the full suite. CI on GitHub must stay green.
- Generated docs are regenerated, never hand-edited: `docs/critic_graph.*` (a test fails on drift), `docs/test_report.md` and `docs/PlacementIQ_Summary.pdf` (after every evaluation run).
- A new dependency needs a one-line justification in `requirements.txt` and an exact version pin. The default answer is no.

## Constraints and do-not-touch
- `PlacementIQ_Project_Spec.md` is a local planning file. It is git-ignored and must never be staged, committed or copied into docs.
- `.env` must never be committed or printed. Never echo `GROQ_API_KEY`.
- **Never put model IDs in code.** They come only from `.env`, because Groq renames and retires models. `scripts/check_models.py` detects a retired ID.
- `evaluation/test_cases.json` is frozen. Editing it invalidates all earlier results.
- Readiness is strict: a required skill counts only if the resume names it (or an alias) in words, and a skill mapped to a syllabus topic weighs `SYLLABUS_SKILL_WEIGHT` times a tool (`checks.readiness_score`).
- Every catalog role has `eligibility` (degree codes or `@group`s from `data/degrees.json`, optional `fields`); a test checks every code exists.
- `data/questions/mcq_bank.csv` is committed; the app must still work without it, and `tests/conftest.py` points the bank at a missing file so tests never depend on its contents. Normalise a new bank with `python -m scripts.verify_and_ingest_mcq --normalise`; every bank topic needs a line in `data/bank_topics.json`.
- `data/role_skills.json` changes readiness and weakness for every student. Edit it only on purpose, and keep each role's topics within its domain's topics in `data/career_catalog.json` (a test enforces this). The five roles the frozen evaluation uses keep the six CS core topics; a student tracks their role's focus topics plus domain topics they quiz.
- The `scripts/seed.py` trajectory (OS and DBMS start weak) is what the demo depends on. Do not change it casually.
- `students.usn` is required (`NOT NULL UNIQUE`). Never drop it or make it optional.
- `schema.sql` has no migrations. A new table (`CREATE TABLE IF NOT EXISTS`, as `plan_progress`) is safe for existing databases; changing an existing table is not, so ask first, and afterwards delete `data/placementiq.db` and reseed.
- Fonts in `static/fonts/` are OFL, self-hosted (no font CDN at runtime: the app must work offline) and keep their licence files next to them.
- External services are optional and degrade in order (Gemini, Groq, Ollama, offline; ElevenLabs, browser voice). Groq's free tier, the one the evaluation used: each model allows 8,000 tokens/minute and 1,000 requests/day (from the response headers), and about 200,000 tokens/day (the full evaluation hit it after 15 of 20 cases). Batch questions into one call, use the small model for extraction, never re-judge questions that were already approved, and keep MOCK_MODE as the default in `.env.example`.
- Two front ends share one core. The Streamlit app and the Next.js app (`frontend/`, through `server.py`) both call `piq.services`; `server.py` only serialises. Its routes are plain `def`s, so the code stays synchronous; the one `async` is FastAPI's lifespan hook. Interview turns stream critic steps as server-sent events, never unchecked tokens.
- Groq keys: `GROQ_API_KEY_1` serves agents a student waits on (interviewer, evaluator, bullet), `GROQ_API_KEY_2` background agents; a 429 fails over once (`piq/llm.py`). `GROQ_API_KEY` alone still works.
- Quizzes in the Next.js app come straight from the question bank (`services.instant_quiz`), with no LLM call; answers stay on the server until `/api/quiz/submit` grades them. The Streamlit quiz keeps the generate -> critic loop with its bank share.
- The bullet polish (`agents.enhance_bullet`) may not invent numbers: `checks.check_bullet` rejects any figure absent from the student's text.
- Telemetry (`database/`): the manager probes `DATABASE_URL` once, with `DB_CONNECT_TIMEOUT`; a missing, malformed, non-PostgreSQL or unreachable URL, or an outage mid-session, fails over to `TELEMETRY_DB_PATH` with one logged event and the operation retried there. No automatic fail-back (restart, or `reset_manager()`). Never log `DATABASE_URL` unmasked: use `safe_url`. `VoiceInterviewSession` stores text and scores only; recording audio or proctoring is still out of scope.
- Voice is limited to speaking questions and transcribing answers; storing audio and video proctoring are out of scope. Also out of scope: auth, a code judge, scraping, a vector database or embeddings, async business logic.
