"""Results: PlacementIQ against a single-prompt baseline on the frozen evaluation cases, each
metric in plain words with the direction that counts as better."""

import streamlit as st

from piq import formatter, services
from piq.ui import page_header

RUN = "python -m evaluation.run_eval --consecutive 5 --interviews"

page_header(
    "Evaluation results",
    "PlacementIQ against a single-prompt baseline on the same 20 frozen test cases, judged "
    "by the same checks and critic.",
)
summary = services.evaluation_summary()
if summary is None:
    st.info(
        "No results yet. Run the evaluation in live mode (it uses about two days of the free "
        "Groq quota), then reload this page:",
        icon=":material/info:",
    )
    st.code(RUN, language="bash")
    st.stop()

if summary.get("mode") == "mock":
    st.warning(
        "These results come from MOCK_MODE: a smoke test, not real measurements.",
        icon=":material/science:",
    )
st.caption(formatter.results_caption(summary))

metrics = formatter.results_metrics(summary)
for start in range(0, len(metrics), 2):
    row = metrics[start : start + 2]  # an odd last metric leaves its row's second column empty
    for column, metric in zip(st.columns(2, gap="medium"), row, strict=False):
        with column, st.container(border=True, height="stretch"):
            st.markdown(f"**{metric.name}** {formatter.direction_md(metric.higher_is_better)}")
            st.caption(metric.definition)
            st.html(formatter.compare_html(metric))

b, p = summary.get("baseline") or {}, summary.get("placementiq") or {}
with st.container(border=True):
    st.markdown(f"**Quiz generations per approved quiz** {formatter.direction_md(False)}")
    st.caption(
        "A cost, not a quality score: the baseline writes one quiz and keeps it; PlacementIQ "
        "writes again whenever the critic sends a flawed draft back."
    )
    with st.container(horizontal=True, gap="large"):
        for system, values in (("Baseline", b), ("PlacementIQ", p)):
            attempts = values.get("avg_quiz_attempts")
            st.metric(system, "—" if attempts is None else f"{attempts:.2f}", width="content")

with st.expander("All numbers as a table", icon=":material/table_rows:"):
    st.dataframe(formatter.results_table(summary).round(2), width="stretch")
    st.caption(formatter.results_note(summary))

if stats := summary.get("agent_stats"):
    st.subheader("Agent cost during the evaluation", anchor=False)
    st.dataframe(
        formatter.agent_table(stats),
        hide_index=True,
        width="stretch",
        column_config={
            "Rejection rate": st.column_config.ProgressColumn(
                "Rejection rate", min_value=0, max_value=100, format="%.0f%%"
            ),
        },
    )
