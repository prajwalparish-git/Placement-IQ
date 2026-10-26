# CLAUDE.md

## Purpose
PlacementIQ is a placement-readiness coach for engineering students. Agents profile a resume, plan the week, set quizzes and run mock interviews. A critic checks every generated output. Quiz results change the next week's plan.

College mini-project scope: one Streamlit process and one SQLite file. Keep it that small.

## Tech stack (pinned in `requirements*.txt`)
| Layer | Choice | Version |
|---|---|---|
| Language | Python | 3.13 (tested on 3.13.3) |
| UI and charts | Streamlit (includes Altair and pandas; both pinned because imported directly) | 1.66.0 (Altair 6.3.0, pandas 3.0.6) |
| Agent loop | LangGraph | 1.2.16 |
| LLM SDK | Groq SDK, JSON mode, built-in retry on 429 | 1.7.0 |
| LLM models (`.env`) | `openai/gpt-oss-120b` (large), `openai/gpt-oss-20b` (small) | verified 2026-10-19 |
| Validation | Pydantic | 2.14.1 |
| Storage | SQLite via stdlib `sqlite3` | stdlib |
| Resume parsing | pypdf / python-docx | 6.21.1 / 1.2.0 |
| Config | python-dotenv | 1.2.4 |
| Dev | pytest / ruff | 9.1.1 / 0.17.1 |
| Dev, visual QA only | Playwright (+ Chromium) / Pillow | 1.64.0 / 12.3.0 |

Playwright drives `scripts/screenshots.py` (never CI or tests); Pillow compresses its PNGs
and is the version Streamlit already installs.

## Directory structure
```
app.py              Entry point: theme CSS, logo, settings check, DB init, sidebar, grouped navigation
views/              One file per page. Calls piq.services, piq.formatter, piq.charts and piq.ui
  home.py           Default page: the loop explained, or readiness, streak and today's focus
  onboard.py        Resume (upload or sample) -> profile; taken-USN confirmation; delete student
  plan.py           Week pills, day-by-day plan with check-off and export, shift and weakness charts
  quiz.py           Topic by weakness + suggested difficulty, critic trail, blank guard, review
  interview.py      Chat mock interview, scored feedback, retry for a failed follow-up, summary
  dashboard.py      Readiness, streak, topic mastery, plans, interviews; agents and critic apart
  results.py        Baseline vs PlacementIQ evaluation results (reads results/summary.json)
piq/                Application package. Only ui.py imports Streamlit
  services.py       Controllers: every user operation; validates, runs agents, persists, typed state
  config.py         Env settings (cached) and constants: topics, thresholds, sizes
  schemas.py        Pydantic models for every LLM output and derived objects
  llm.py            The ONLY LLM gateway: JSON mode, validation, repair retry, agent_logs, mock
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
static/             Served at app/static: app.css, brand/ (mark, wordmark), fonts/ (OFL woff2)
data/
  role_skills.json  Role -> required skill -> syllabus topic (drives readiness and weakness)
  sample_resumes/   Three fictional resumes (TXT)
  placementiq.db    Runtime database (git-ignored; created on first run)
evaluation/
  test_cases.json   20 frozen cases (5 roles x 4 score profiles)
  run_eval.py       Baseline (one prompt) vs PlacementIQ; resumable, checkpointed; writes results/
  report.py         results/summary.json -> report.md (tables) + chart.svg for the report
scripts/
  seed.py           Demo student DEMO0001 with 4 weeks of history (no LLM calls)
  check_models.py   Are the configured Groq models served, JSON-capable, and within quota?
  export_graph.py   Mermaid of the compiled graph -> docs/critic_graph.mmd + .md
  test_report.py    Runs pytest and writes docs/test_report.md (test-case table)
  screenshots.py    Dev: every page and flow via Playwright, 3 widths x 2 schemes; fails on console errors
  perf.py           Dev: render time and queries per page via AppTest (--mode fresh | rerun)
  tunnel.ps1 / .bat Demo: the app on a temporary public URL (Cloudflare quick tunnel; Windows)
docs/               diagrams.md (use case, DFD, ER, sequence), critic graph, test report, performance.md
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
streamlit run app.py                    # dev server, http://localhost:8501
pytest                                  # all tests, offline, about 2 min
ruff format . ; ruff check .            # format + lint (must be clean)
python -m evaluation.run_eval --consecutive 5 --interviews   # live; ~360k tokens = 2 days of quota
python -m evaluation.run_eval --consecutive 5 --interviews --resume   # continue (same flags)
python -m evaluation.report             # results/report.md + chart.svg
python -m scripts.test_report           # docs/test_report.md from a real test run
python -m scripts.export_graph          # refresh docs/critic_graph.mmd and .md
python -m scripts.screenshots docs/design/after [--pages quiz] [--widths 1440,390]   # visual review
python -m scripts.perf docs/design/perf.md [--mode rerun]   # render time per page
```
There is no build step. `.env.example` already contains the verified model IDs. Live mode needs `GROQ_API_KEY` and `MOCK_MODE=false`.

## Coding conventions
- Format and lint with ruff (`pyproject.toml`: line length 100, py313, rules E F W I B UP SIM). Leave no lint errors.
- Type hints on every function signature. Use PEP 695 generics (`def f[T](...)`), not `TypeVar`.
- Layering: `views -> services -> agents -> graph -> llm`, with `db` used by `services` and `llm`. Views never import `agents` or `db`.
- `services` validate every input and raise `ServiceError` with a message safe to show users. They return typed state, for example `InterviewSession`, `QuizResult` and `PlanOverview`.
- Every LLM output is a Pydantic model returned by `piq.llm.call`. Never parse prose, and never call the Groq SDK from anywhere else (the one exception is `scripts/check_models.py`).
- If code can compute something, code computes it: readiness, missing skills, weakness, weak-topic share, minute ordering, difficulty, overall score, turn bookkeeping. The LLM only does what needs language.
- New generation tasks are a `graph.Task(name, generate, verify)` run through `graph.run` / `run_or_raise`. `generate(inputs, reasons, previous)` receives the rejection reasons and the rejected output. `verify` returns reasons as text.
- Problems with a single quiz question must be built with `checks.question_reason(i, msg)`. Then only that question is regenerated.
- Put cheap deterministic checks in `checks.py` and run them before any LLM critic call.
- All SQL lives in `piq/db.py` and uses `?` parameters. Never build SQL with f-strings. Agents never write domain tables; services do.
- Prompts live only in `piq/prompts.py`. Constants and thresholds live only in `piq/config.py`.
- Views stay thin: no business logic, and rendering goes through `formatter.py` and `charts.py`.
- **Theme first, CSS last.** Colours, fonts and radii live in `.streamlit/config.toml` (light and dark), mirrored by `config.PALETTE`, `SEMANTIC_COLORS` and `TOPIC_COLORS`; `tests/test_theme.py` checks contrast and that both agree. `static/app.css` (under 150 lines and 8 KB) holds only what the theme cannot express: every selector includes a `data-testid` (own classes only beneath one, never `.st-emotion-cache-*`), every colour is a `PALETTE` token written `light-dark(light, dark)`, and each rule says why it exists.
- **Topic colours mean topics.** Every topic chart, chip and legend uses `TOPIC_COLORS` (charts get them from the theme's categorical palette with a fixed `TOPICS` domain). Never use them for status; every status shows an icon and words, never colour alone.
- **Escape every dynamic value.** Resume, LLM and user text go through `formatter.md_escape` in Markdown and `html.escape` in HTML builders (`st.html`); tests feed `<script>`, `*p`, `__init__` and image Markdown through each builder.
- **Charts** are pure builders in `charts.py` returning `alt.Chart` (tests check encodings); views render the matching `*_spec` (plain Vega-Lite cached per distinct data) with `st.vega_lite_chart`. Titles state the takeaway as text above the chart; every mark has a tooltip.
- Icons are Material Symbols (`:material/name:`), never emoji. Copy is sentence case, British spelling, no exclamation marks.
- **Screenshot review loop** for any page change: `python -m scripts.screenshots docs/design/after --pages <page>`, open the PNGs at every width and in both schemes, fix, capture again. Zero browser console errors.
- Code is synchronous only (no asyncio), because of Streamlit.
- Each module starts with a docstring stating its job; add comments only for non-obvious reasons.
- Every change ships with a test. Tests must pass offline in MOCK_MODE. Any new mock response must pass the same schema and checks as real output.
- Tests never read the real `.env`: `tests/conftest.py` points `PIQ_DOTENV` at a missing file, clears caches and gives each test a fresh database. Live code paths are tested with fake Groq clients (`tests/test_llm.py`, `tests/test_check_models.py`).
- Commits follow Conventional Commits (`feat(scope): …`, `fix(scope): …`), one logical unit per commit, and every commit passes the full suite. CI on GitHub must stay green.
- Generated docs are regenerated, never hand-edited: `docs/critic_graph.*` (a test fails on drift) and `docs/test_report.md`.
- A new dependency needs a one-line justification in `requirements.txt` and an exact version pin. The default answer is no.

## Constraints and do-not-touch
- `PlacementIQ_Project_Spec.md` is a local planning file. It is git-ignored and must never be staged, committed or copied into docs.
- `.env` must never be committed or printed. Never echo `GROQ_API_KEY`.
- **Never put model IDs in code.** They come only from `.env`, because Groq renames and retires models. `scripts/check_models.py` detects a retired ID.
- `evaluation/test_cases.json` is frozen. Editing it invalidates all earlier results.
- `data/role_skills.json` changes readiness and weakness for every student. Edit it only on purpose, and keep its topics within `Aptitude, DBMS, OS, CN, DSA, OOP` (a test enforces this).
- The `scripts/seed.py` trajectory (OS and DBMS start weak) is what the demo depends on. Do not change it casually.
- `students.usn` is required (`NOT NULL UNIQUE`). Never drop it or make it optional.
- `schema.sql` has no migrations. A new table (`CREATE TABLE IF NOT EXISTS`, as `plan_progress`) is safe for existing databases; changing an existing table is not, so ask first, and afterwards delete `data/placementiq.db` and reseed.
- Fonts in `static/fonts/` are OFL, self-hosted (no font CDN at runtime: the app must work offline) and keep their licence files next to them.
- Groq's free tier is the only external service: each model allows 8,000 tokens/minute and 1,000 requests/day (from the response headers), and about 200,000 tokens/day (the full evaluation hit it after 15 of 20 cases). Batch questions into one call, use the small model for extraction, never re-judge questions that were already approved, and keep MOCK_MODE as the default in `.env.example`.
- Out of scope: auth, voice/video, a code judge, scraping, a vector database or embeddings, async, a separate HTTP backend (services are the API surface).
