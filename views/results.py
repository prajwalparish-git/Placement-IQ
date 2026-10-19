import pandas as pd
import streamlit as st

from piq import formatter, services

st.header("Evaluation results")
st.caption("Single-prompt baseline vs PlacementIQ on the 20 frozen test cases.")
summary = services.evaluation_summary()
if summary is None:
    st.info(
        "No results yet. Run `python -m evaluation.run_eval` in live mode "
        "(add `--consecutive 5 --interviews` for every metric)."
    )
    st.stop()

if summary.get("mode") == "mock":
    st.warning("These results come from MOCK_MODE: a smoke test, not real measurements.")
st.caption(formatter.results_caption(summary))

table = formatter.results_table(summary)
st.dataframe(table.round(2), width="stretch")
st.bar_chart(table.drop(index=formatter.ATTEMPTS, errors="ignore"), horizontal=True, stack=False)
st.caption(
    "Rates run from 0 to 1; higher is better except the duplicate rate. "
    "Confirm quiz validity by hand with evaluation/results/questions.csv."
)

if stats := summary.get("agent_stats"):
    st.subheader("Agent cost during the evaluation")
    st.dataframe(pd.DataFrame(stats).set_index("agent_name"), width="stretch")
