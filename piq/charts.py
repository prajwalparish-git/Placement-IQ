"""Chart builders: data in, alt.Chart out. Pure (Altair, no Streamlit), so encodings are
unit-tested.

Colour comes from the active Streamlit theme, so charts follow the light/dark switch:
topic series use a fixed domain (TOPICS) and no range, and Streamlit fills it with that
scheme's chartCategoricalColors, which config.toml lists in TOPICS order. OS is therefore
the same colour in every chart. Neutral marks keep the theme's defaults.

Views render the `*_spec` functions with st.vega_lite_chart: the same charts as plain
Vega-Lite, built once per distinct data (see the note above them).
"""

import json
import math
from collections.abc import Mapping
from functools import lru_cache

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


def minutes_shift(
    before: Mapping[str, int], after: Mapping[str, int], weeks: tuple[int, int]
) -> alt.LayerChart:
    """Minutes per topic in two weeks as a dumbbell: a hollow grey dot for the earlier week, a
    filled dot in the topic's colour for the later one, joined by a line, so the shift reads
    as movement and the weeks differ by shape, not colour alone. Axis labels carry the
    numbers ("OS  600 → 840"); the busiest topic comes first."""
    df = pd.DataFrame(
        {
            "topic": list(TOPICS),
            "before": [int(before.get(t, 0)) for t in TOPICS],
            "after": [int(after.get(t, 0)) for t in TOPICS],
        }
    )
    df["change"] = df["after"] - df["before"]
    df["label"] = [f"{t}  {b} → {a}" for t, b, a in zip(df.topic, df.before, df.after, strict=True)]
    order = df.sort_values(["after", "before"], ascending=False, kind="stable")["label"].tolist()
    y = alt.Y(
        "label:N",
        sort=order,
        title=None,
        axis=alt.Axis(labelFontSize=14, labelPadding=8, labelLimit=0),  # never cut a number
    )
    # Three ticks in whole hours (0, half, top) stay apart on a phone.
    top = max(60, 60 * math.ceil(int(df[["before", "after"]].max().max()) / 60))
    scale = alt.Scale(domain=[0, top])
    axis = alt.Axis(title=None, format="d", values=[0, top // 2, top])
    tooltip = [
        alt.Tooltip("topic:N", title="Topic"),
        alt.Tooltip("before:Q", title=f"Week {weeks[0]} (min)"),
        alt.Tooltip("after:Q", title=f"Week {weeks[1]} (min)"),
        alt.Tooltip("change:Q", title="Change (min)", format="+d"),
    ]
    base = alt.Chart(df).encode(y=y, tooltip=tooltip)
    line = base.mark_rule(strokeWidth=2, color=NEUTRAL, opacity=0.6).encode(
        x=alt.X("before:Q", scale=scale, axis=axis), x2="after:Q"
    )
    earlier = base.mark_point(size=110, strokeWidth=2, color=NEUTRAL, filled=False).encode(
        x=alt.X("before:Q", scale=scale, axis=axis)
    )
    later = base.mark_circle(size=150, opacity=1).encode(
        x=alt.X("after:Q", scale=scale, axis=axis),
        color=alt.Color("topic:N", scale=TOPIC_SCALE, legend=None),
    )
    return themed(alt.layer(line, earlier, later).properties(height=ROW_PX * len(df)))


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


# --- specs for the views ----------------------------------------------------------------
# Layering and validating an Altair chart costs 40-60 ms, on every rerun. The views
# therefore render plain Vega-Lite specs, built once per distinct data and cached as JSON
# text (immutable; each caller gets a fresh dict). Keyed by the values, never by student, so
# a cached spec is right for whoever asks, after any write.


def to_spec(chart: alt.TopLevelMixin) -> dict:
    """The chart as a Vega-Lite dict with its data inline. Altair's schema check is skipped
    (the builders are unit-tested) and so is the default size Altair's theme adds, because
    Streamlit sizes charts itself."""
    spec = chart.to_dict(validate=False)
    view = spec.get("config", {}).get("view", {})
    for key in ("continuousWidth", "continuousHeight"):
        view.pop(key, None)
    return spec


def weakness_spec(weakness: Mapping[str, float]) -> dict:
    return json.loads(_weakness_json(tuple(weakness.items())))


@lru_cache(maxsize=128)
def _weakness_json(items: tuple[tuple[str, float], ...]) -> str:
    return json.dumps(to_spec(weakness_bars(dict(items))))


def minutes_shift_spec(
    before: Mapping[str, int], after: Mapping[str, int], weeks: tuple[int, int]
) -> dict:
    return json.loads(_minutes_shift_json(tuple(before.items()), tuple(after.items()), weeks))


@lru_cache(maxsize=128)
def _minutes_shift_json(
    before: tuple[tuple[str, int], ...], after: tuple[tuple[str, int], ...], weeks: tuple[int, int]
) -> str:
    return json.dumps(to_spec(minutes_shift(dict(before), dict(after), weeks)))


def readiness_ring_spec(score: int) -> dict:
    return json.loads(_readiness_ring_json(score))


@lru_cache(maxsize=128)
def _readiness_ring_json(score: int) -> str:
    return json.dumps(to_spec(readiness_ring(score)))
