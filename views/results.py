"""Results: PlacementIQ against a single-prompt baseline on the frozen evaluation cases,
judged on a scorecard of advanced parameters. Each says what it measures and how, shows
both systems' measured values, and rates them out of 10."""

import streamlit as st

from piq import formatter, services
from piq.ui import page_header

RUN = "python -m evaluation.run_eval --consecutive 5 --interviews"

page_header(
    "Evaluation results",
    "PlacementIQ against a single-prompt baseline on the same 20 frozen test cases, judged "
    "by the same checks and critic, and scored on the parameters below.",
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

card = services.evaluation_scorecard(summary)

# --- overall ---------------------------------------------------------------------------
with st.container(border=True):
    st.subheader("Overall rating", anchor=False)
    columns = st.columns(2, gap="large")
    for column, system, label in zip(
        columns, ("placementiq", "baseline"), ("PlacementIQ", "Baseline"), strict=True
    ):
        score = card.overall(system)
        with column:
            st.metric(label, formatter.score_text(score), width="content")
            st.markdown(formatter.rating_md(score))
    piq, base = card.overall("placementiq", True), card.overall("baseline", True)
    st.caption(
        "A weighted mean of the parameter scores below (validity counts double; the cue and "
        "cost parameters half). Over only the parameters measured for both systems, "
        f"PlacementIQ scores {formatter.score_text(piq)} and the baseline "
        f"{formatter.score_text(base)}. Ratings: 9 or more excellent, 7 good, 5 fair, "
        "below 5 needs work."
    )

# --- parameters, by group ------------------------------------------------------------
for group in card.groups():
    st.subheader(group, anchor=False)
    params = [p for p in card.parameters if p.group == group]
    for start in range(0, len(params), 2):
        row = params[start : start + 2]  # an odd last card leaves its row's second column empty
        for column, p in zip(st.columns(2, gap="medium"), row, strict=False):
            with column, st.container(border=True, height="stretch"):
                st.markdown(
                    f"**{p.name}** {formatter.direction_md(p.higher_is_better)}  \n"
                    f":gray[PlacementIQ:] {formatter.rating_md(p.placementiq_score)} "
                    f":gray[Baseline:] {formatter.rating_md(p.baseline_score)}"
                )
                st.markdown(p.what)
                st.html(formatter.scorecard_compare_html(p))
                st.caption(f"How: {p.method}")
                if p.note:
                    st.caption(p.note)

with st.expander("Every parameter as a table", icon=":material/table_rows:"):
    st.dataframe(formatter.scorecard_table(card), width="stretch")
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
