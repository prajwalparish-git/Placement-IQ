"""Chart builders: marks, encodings, colour scale, number formats and titles (no rendering)."""

from piq import charts
from piq.config import TOPICS, WEAK_THRESHOLD

WEAKNESS = {"Aptitude": 0.37, "DBMS": 0.4, "OS": 0.43, "CN": 0.4, "DSA": 0.23, "OOP": 0.13}


def _rows(spec: dict, layer: dict) -> list[dict]:
    return spec["datasets"][layer["data"]["name"]]


def test_weakness_bars_run_weakest_first_in_topic_colours():
    spec = charts.weakness_bars(WEAKNESS).to_dict()
    bars, threshold = spec["layer"]
    assert [layer["mark"]["type"] for layer in spec["layer"]] == ["bar", "rule"]
    y = bars["encoding"]["y"]
    # Direct labels: each axis label carries the topic and its value, weakest first.
    assert y["field"] == "label" and y["sort"] == [
        "OS  43%",
        "DBMS  40%",
        "CN  40%",
        "Aptitude  37%",
        "DSA  23%",
        "OOP  13%",
    ]
    color = bars["encoding"]["color"]
    # The domain pins the order; the range is left to the theme's per-scheme topic palette.
    assert color["field"] == "topic" and color["scale"] == {"domain": list(TOPICS)}
    assert color["legend"] is None
    x_axis = bars["encoding"]["x"]["axis"]
    assert x_axis["format"] == "%" and x_axis["values"] == [0, WEAK_THRESHOLD, 1]
    assert _rows(spec, threshold) == [{"weakness": WEAK_THRESHOLD}]
    assert threshold["mark"]["color"] == charts.NEUTRAL and threshold["mark"]["strokeDash"]
    assert all("tooltip" in layer["encoding"] for layer in spec["layer"])
    assert "title" not in spec  # views show the takeaway as text, which wraps on a phone
    assert spec["height"] == charts.ROW_PX * len(WEAKNESS)


def test_weakness_bars_take_an_optional_takeaway_title():
    spec = charts.weakness_bars(WEAKNESS, "OS is your weakest topic").to_dict()
    assert spec["title"] == "OS is your weakest topic"


def test_minutes_shift_is_a_dumbbell_from_grey_to_topic_colour():
    spec = charts.minutes_shift({"OS": 600, "DBMS": 360}, {"OS": 840, "DBMS": 0}, (3, 4)).to_dict()
    line, earlier, later = spec["layer"]
    assert [layer["mark"]["type"] for layer in spec["layer"]] == ["rule", "point", "circle"]
    assert line["encoding"]["x"]["field"] == "before" and line["encoding"]["x2"]["field"] == "after"
    # The weeks differ by shape (hollow vs filled), not colour alone.
    assert earlier["mark"]["filled"] is False and earlier["mark"]["color"] == charts.NEUTRAL
    assert later["encoding"]["x"]["field"] == "after"
    assert later["encoding"]["color"]["scale"] == {"domain": list(TOPICS)}
    y = later["encoding"]["y"]
    assert all(layer["encoding"]["y"] == y for layer in spec["layer"])
    assert y["sort"][:2] == ["OS  600 → 840", "DBMS  360 → 0"]  # busiest first
    assert y["axis"]["labelLimit"] == 0  # numbers in labels are never cut off
    assert later["encoding"]["x"]["axis"]["values"] == [0, 420, 840]  # whole hours
    assert len(y["sort"]) == len(TOPICS)
    rows = spec["datasets"][spec["data"]["name"]]
    assert {r["topic"]: r["change"] for r in rows}["DBMS"] == -360
    titles = [t["title"] for t in later["encoding"]["tooltip"]]
    assert titles == ["Topic", "Week 3 (min)", "Week 4 (min)", "Change (min)"]
    assert spec["height"] == charts.ROW_PX * len(TOPICS)


def test_readiness_ring_fills_the_score_in_the_brand_teal():
    spec = charts.readiness_ring(42).to_dict()
    assert spec["mark"]["type"] == "arc"
    assert spec["datasets"][spec["data"]["name"]] == [
        {"part": "Ready", "value": 42, "order": 0},
        {"part": "To go", "value": 58, "order": 1},
    ]
    scale = spec["encoding"]["color"]["scale"]
    assert scale == {"domain": ["Ready", "To go"], "range": [charts.BRAND_COLOR, charts.NEUTRAL]}
    assert "tooltip" in spec["encoding"]


def test_shared_theme_sets_fonts_and_drops_the_frame():
    config = charts.weakness_bars(WEAKNESS, "t").to_dict()["config"]
    assert config["font"] == "Atkinson Hyperlegible Next"
    assert config["view"]["strokeWidth"] == 0
    assert (config["title"]["font"], config["title"]["anchor"]) == ("Bricolage Grotesque", "start")
    assert config["axis"]["domain"] is False and config["axis"]["ticks"] is False


def test_view_specs_are_the_charts_as_plain_vega_lite_without_altairs_size_default():
    spec = charts.weakness_spec(WEAKNESS)
    assert spec == charts.to_spec(charts.weakness_bars(WEAKNESS))
    assert [layer["mark"]["type"] for layer in spec["layer"]] == ["bar", "rule"]
    assert "continuousWidth" not in spec["config"]["view"]  # Streamlit sizes charts
    assert spec["config"]["view"]["strokeWidth"] == 0  # the shared look survives
    [rows] = [v for v in spec["datasets"].values() if len(v) == len(WEAKNESS)]
    assert {r["topic"] for r in rows} == set(WEAKNESS)  # data travels inline


def test_cached_specs_hand_out_fresh_copies():
    first = charts.minutes_shift_spec({"OS": 600}, {"OS": 840}, (3, 4))
    first["layer"].clear()  # a caller changing its copy must not change the next one
    again = charts.minutes_shift_spec({"OS": 600}, {"OS": 840}, (3, 4))
    assert len(again["layer"]) == 3
    assert charts.readiness_ring_spec(42) == charts.to_spec(charts.readiness_ring(42))
    assert charts.readiness_ring_spec(42) is not charts.readiness_ring_spec(42)


def test_score_spark_draws_one_topic_in_its_colour_without_axes():
    spec = charts.score_spark("OS", [30, 40, 70]).to_dict()
    line, points = spec["layer"]
    assert [line["mark"]["type"], points["mark"]["type"]] == ["line", "circle"]
    enc = line["encoding"]
    assert enc["x"]["axis"] is None and enc["y"]["axis"] is None
    assert enc["y"]["scale"]["domain"] == [0, 100]
    assert enc["color"]["scale"] == {"domain": list(TOPICS)}
    rows = spec["datasets"][spec["data"]["name"]]
    assert [(r["topic"], r["attempt"], r["score"]) for r in rows] == [
        ("OS", 1, 30.0),
        ("OS", 2, 40.0),
        ("OS", 3, 70.0),
    ]
    assert "tooltip" in enc
    one = charts.score_spark("CN", [50]).to_dict()  # a single quiz still gets an x range
    assert one["layer"][0]["encoding"]["x"]["scale"]["domain"] == [1, 2]


def test_week_mix_stacks_topics_in_order_per_week():
    spec = charts.week_mix({1: {"OS": 300, "DBMS": 120}, 2: {"OS": 420, "CN": 0}}).to_dict()
    enc = spec["encoding"]
    assert spec["mark"]["type"] == "bar"
    assert enc["y"]["sort"] == ["Week 1", "Week 2"]
    assert enc["color"]["scale"] == {"domain": list(TOPICS)} and enc["order"]["field"] == "rank"
    rows = spec["datasets"][spec["data"]["name"]]
    assert ("Week 2", "CN") not in {(r["week"], r["topic"]) for r in rows}  # no empty segment
    assert {r["topic"]: r["rank"] for r in rows} == {"OS": 2, "DBMS": 1}
    assert spec["height"] == charts.ROW_PX * 2 + charts.LEGEND_PX  # axis and legend fit inside
    assert enc["color"]["legend"]["columns"] == 3  # wraps on a phone


def test_interview_trend_is_a_0_to_5_line_in_the_brand_teal():
    spec = charts.interview_trend([2.5, 3.75], ["19 Oct, HR", "20 Oct, HR"]).to_dict()
    line, points = spec["layer"]
    assert line["mark"]["color"] == points["mark"]["color"] == charts.BRAND_COLOR
    y = line["encoding"]["y"]
    assert y["scale"]["domain"] == [0, 5] and y["axis"]["values"] == [0, 2.5, 5]
    assert [t["title"] for t in line["encoding"]["tooltip"]] == ["Session", "Average (/5)"]


def test_readiness_trend_is_a_0_to_100_line_per_profile():
    spec = charts.readiness_trend([42, 58], ["19 Oct", "26 Oct"]).to_dict()
    line, points = spec["layer"]
    assert line["mark"]["color"] == points["mark"]["color"] == charts.BRAND_COLOR
    y = line["encoding"]["y"]
    assert y["scale"]["domain"] == [0, 100] and y["axis"]["values"] == [0, 50, 100]
    assert line["encoding"]["x"]["axis"]["labelExpr"] == "'Profile ' + datum.value"
    rows = spec["datasets"][spec["data"]["name"]]
    assert [(r["n"], r["value"]) for r in rows] == [(1, 42.0), (2, 58.0)]
    assert charts.readiness_trend_spec([42, 58], ["a", "b"]) == charts.to_spec(
        charts.readiness_trend([42, 58], ["a", "b"])
    )


def test_dashboard_specs_match_their_charts():
    assert charts.score_spark_spec("OS", [30, 70]) == charts.to_spec(
        charts.score_spark("OS", [30, 70])
    )
    weeks = {1: {"OS": 420}}
    assert charts.week_mix_spec(weeks) == charts.to_spec(charts.week_mix(weeks))
    assert charts.interview_trend_spec([3.0], ["x"]) == charts.to_spec(
        charts.interview_trend([3.0], ["x"])
    )


def test_activity_heatmap_is_a_12_week_calendar_with_neutral_empty_days():
    from datetime import date

    today = date(2026, 10, 20)  # a Tuesday
    spec = charts.activity_heatmap({date(2026, 10, 19): 2, date(2026, 8, 3): 1}, today).to_dict()
    assert spec["mark"]["type"] == "rect"
    rows = spec["datasets"][spec["data"]["name"]]
    assert rows[0] == {"date": "2026-08-03", "week": 0, "weekday": "Mon", "count": 1}
    assert rows[-1]["date"] == "2026-10-20" and rows[-1]["week"] == 11  # no future days
    assert len(rows) == 7 * 11 + 2
    enc = spec["encoding"]
    assert enc["y"]["sort"] == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    assert enc["color"] == {
        "condition": {"test": "(datum.count === 0)", "value": charts.NEUTRAL},  # no study
        "value": charts.BRAND_COLOR,
    }
    opacity = enc["opacity"]  # stronger for busier days, never lighter than an empty one
    assert opacity["condition"]["value"] == 0.18 and opacity["field"] == "count"
    assert opacity["scale"]["range"] == [0.5, 1]
    assert [t["title"] for t in enc["tooltip"]] == ["Day", "Quizzes and interviews"]
    assert charts.activity_heatmap_spec({date(2026, 10, 19): 2}, today) == charts.to_spec(
        charts.activity_heatmap({date(2026, 10, 19): 2}, today)
    )
