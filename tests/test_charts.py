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
