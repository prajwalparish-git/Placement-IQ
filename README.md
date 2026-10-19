# PlacementIQ

An adaptive multi-agent placement-readiness coach. It profiles a resume against a target role, writes a weekly study plan, sets adaptive quizzes and runs mock interviews. A critic agent checks every generated output and forces a regeneration when the output fails. Quiz scores feed back into the next week's plan.

## Quick start (offline, no API key)
```
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.seed            # demo student DEMO0001 with 4 weeks of history
streamlit run app.py
```
Without a `.env` file the app runs in **MOCK_MODE**: canned responses and no network.

## Live mode (Groq free tier)
1. Copy `.env.example` to `.env` and set `GROQ_API_KEY`.
2. Set `MOCK_MODE=false`. The model IDs are already filled in (`openai/gpt-oss-120b` and `openai/gpt-oss-20b`, verified 2026-10-19).
3. Before a demo, run `python -m scripts.check_models`. It confirms both models are still served, that JSON mode works, and how much quota is left (each model allows 8,000 tokens/minute and 1,000 requests/day).

## Deploy (optional): Streamlit Community Cloud
1. On share.streamlit.io choose **Create app**, pick this repository (a private repo needs GitHub access granted to Streamlit), branch `main`, main file `app.py`, and Python 3.13 under **Advanced settings**.
2. Under **Secrets**, add:
   ```toml
   GROQ_API_KEY = "your key"
   GROQ_MODEL_LARGE = "openai/gpt-oss-120b"
   GROQ_MODEL_SMALL = "openai/gpt-oss-20b"
   MOCK_MODE = "false"
   SEED_DEMO = "true"
   ```
   Streamlit exposes top-level secrets as environment variables, so no code change is needed.
3. The hosted disk is not persistent: the SQLite file resets when the app restarts. With `SEED_DEMO=true` the demo student is recreated on start, so the demo always opens with history.

## Demo path
1. **Onboard:** pick a sample resume. You see the profile, missing skills and readiness.
2. **Weekly plan:** generate a week. Weak topics get the most minutes.
3. **Quiz:** take one and score low on purpose. When the critic rejects a question, the status box shows it, and only that question is regenerated.
4. **Weekly plan:** generate the next week. The weakest topic now gets the most minutes, and the chart shows the shift.
5. **Mock interview:** give a vague answer and get a probing follow-up and a rubric score.
6. **Dashboard:** trends, plus agent latency, tokens and critic rejection rate.
7. **Results:** baseline vs PlacementIQ table and chart from the evaluation.

## Tests and evaluation
```
pip install -r requirements-dev.txt
pytest                                   # offline, includes headless UI tests (CI runs it on every push)
python -m evaluation.run_eval --consecutive 5 --interviews   # live, 20 frozen cases, ~290 calls
python -m evaluation.run_eval --resume   # continue after the daily quota runs out
python -m evaluation.report              # results/report.md + chart.svg for the report
```

## Documentation
- [ARCHITECTURE.md](ARCHITECTURE.md): design, data flow, decisions, limitations
- [CLAUDE.md](CLAUDE.md): code map, commands and conventions
- [docs/diagrams.md](docs/diagrams.md): use case, components, DFD level 0/1, ER and sequence diagrams
- [docs/critic_graph.md](docs/critic_graph.md): the LangGraph critic loop, generated from the code
- [docs/test_report.md](docs/test_report.md): every test case and its result (`python -m scripts.test_report`)
