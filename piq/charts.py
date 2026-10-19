"""Chart builders: data in, alt.Chart out. Pure (Altair, no Streamlit), so encodings are
unit-tested.

Colour comes from the active Streamlit theme, so charts follow the light/dark switch:
topic series use a fixed domain (TOPICS) and no range, and Streamlit fills it with that
scheme's chartCategoricalColors, which config.toml lists in TOPICS order. OS is therefore
the same colour in every chart. Neutral marks keep the theme's defaults.
"""

from collections.abc import Mapping

import altair as alt
import pandas as pd

from piq.config import BRAND_COLOR, PALETTE, TOPICS, WEAK_THRESHOLD

FONT = "Atkinson Hyperlegible Next"
HEADING_FONT = "Bricolage Grotesque"
TOPIC_SCALE = alt.Scale(domain=list(TOPICS))
ROW_PX = 34  # one horizontal bar plus breathing room
# Marks that must read in either scheme (Vega cannot follow the theme switch for them):
# this grey keeps >= 3:1 on both page backgrounds.
NEUTRAL = PALETTE["light"]["border"]


def themed[C: alt.TopLevelMixin](chart: C) -> C:
    """The shared look: theme fonts, no frame, quiet axes, a left-aligned takeaway title."""
    return (
        chart.configure(font=FONT)
        .configure_view(strokeWidth=0)
        .configure_axis(
            labelFontSize=13,
            titleFontSize=13,
            labelPadding=6,
            domain=False,
            ticks=False,
            gridOpacity=0.5,
        )
        .configure_title(font=HEADING_FONT, fontSize=17, fontWeight=600, anchor="start", offset=12)
    )


def weakness_bars(weakness: Mapping[str, float], title: str | None = None) -> alt.LayerChart:
    """Weakness per topic as horizontal bars, weakest first, with the weak threshold dashed.
    Each axis label carries the topic and its value ("OS  43%"): a direct label that the
    theme colours correctly in both schemes, where text marks do not."""
    df = pd.DataFrame({"topic": list(weakness), "weakness": [float(v) for v in weakness.values()]})
    df["label"] = [f"{t}  {w:.0%}" for t, w in zip(df["topic"], df["weakness"], strict=True)]
    order = df.sort_values("weakness", ascending=False, kind="stable")["label"].tolist()
    y = alt.Y("label:N", sort=order, title=None, axis=alt.Axis(labelFontSize=14, labelPadding=8))
    x = alt.X(
        "weakness:Q",
        scale=alt.Scale(domain=[0, 1]),
        # Three ticks: they stay apart on a phone, and 50% is the weak threshold.
        axis=alt.Axis(format="%", values=[0, WEAK_THRESHOLD, 1], title=None),
    )
    tooltip = [
        alt.Tooltip("topic:N", title="Topic"),
        alt.Tooltip("weakness:Q", title="Weakness", format=".0%"),
    ]
    bars = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=4, size=18)
        .encode(
            y=y, x=x, color=alt.Color("topic:N", scale=TOPIC_SCALE, legend=None), tooltip=tooltip
        )
    )
    threshold = (
        alt.Chart(pd.DataFrame({"weakness": [WEAK_THRESHOLD]}))
        .mark_rule(strokeDash=[4, 4], strokeWidth=1.5, color=NEUTRAL)
        .encode(x="weakness:Q", tooltip=alt.value(f"Weak above {WEAK_THRESHOLD:.0%}"))
    )
    layered = alt.layer(bars, threshold).properties(height=ROW_PX * len(df))
    return themed(layered.properties(title=title) if title else layered)


def readiness_ring(score: int) -> alt.Chart:
    """Readiness out of 100 as a ring: the filled arc in the brand teal (>= 3:1 in both
    schemes), the rest a faint track. The number itself is shown next to it as text."""
    df = pd.DataFrame({"part": ["Ready", "To go"], "value": [score, 100 - score], "order": [0, 1]})
    ring = (
        alt.Chart(df)
        .mark_arc(innerRadius=34, outerRadius=52)
        .encode(
            theta=alt.Theta("value:Q", stack=True),
            order=alt.Order("order:Q"),
            color=alt.Color(
                "part:N",
                scale=alt.Scale(domain=["Ready", "To go"], range=[BRAND_COLOR, NEUTRAL]),
                legend=None,
            ),
            opacity=alt.condition(alt.datum.part == "Ready", alt.value(1.0), alt.value(0.25)),
            tooltip=[alt.Tooltip("part:N", title=" "), alt.Tooltip("value:Q", title="Points")],
        )
        .properties(width=112, height=112)
    )
    return themed(ring)
