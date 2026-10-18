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
1. Copy `.env.example` to `.env`.
2. Set `GROQ_API_KEY`, `GROQ_MODEL_LARGE` and `GROQ_MODEL_SMALL`, using current model IDs from the Groq console.
3. Set `MOCK_MODE=false`.

## Demo path
1. **Onboard:** pick a sample resume. You see the profile, missing skills and readiness.
2. **Weekly plan:** generate a week. Weak topics get the most minutes.
3. **Quiz:** take one and score low on purpose. The status box shows the critic rejecting and regenerating.
4. **Weekly plan:** generate the next week. The chart shows minutes moving toward the low-scoring topic.
5. **Mock interview:** give a vague answer and get a probing follow-up and a rubric score.
6. **Dashboard:** trends, plus agent latency, tokens and critic rejection rate.

## Tests and evaluation
```
pip install -r requirements-dev.txt
pytest                                   # offline, includes headless UI tests
python -m evaluation.run_eval            # baseline vs PlacementIQ on 20 frozen cases (live mode)
python -m scripts.export_graph           # docs/critic_graph.mmd for the report
```

See [CLAUDE.md](CLAUDE.md) for the code map and conventions, and [ARCHITECTURE.md](ARCHITECTURE.md) for the design.
