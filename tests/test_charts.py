"""Chart builders: marks, encodings, colour scale, number formats and titles (no rendering)."""

from piq import charts
from piq.config import TOPICS, WEAK_THRESHOLD

WEAKNESS = {"Aptitude": 0.37, "DBMS": 0.4, "OS": 0.43, "CN": 0.4, "DSA": 0.23, "OOP": 0.13}


def _rows(spec: dict, layer: dict) -> list[dict]:
    return spec["datasets"][layer["data"]["name"]]


def test_weakness_bars_run_weakest_first_in_topic_colours():
    spec = charts.weakness_bars(WEAKNESS, "OS is your weakest topic").to_dict()
    bars, values, threshold = spec["layer"]
    assert [layer["mark"]["type"] for layer in spec["layer"]] == ["bar", "text", "rule"]
    y = bars["encoding"]["y"]
    assert y["field"] == "topic" and y["sort"] == ["OS", "DBMS", "CN", "Aptitude", "DSA", "OOP"]
    color = bars["encoding"]["color"]
    # The domain pins the order; the range is left to the theme's per-scheme topic palette.
    assert color["scale"] == {"domain": list(TOPICS)} and color["legend"] is None
    assert bars["encoding"]["x"]["axis"]["format"] == "%"
    assert values["encoding"]["text"]["format"] == ".0%"  # direct labels instead of a legend
    assert _rows(spec, threshold) == [{"weakness": WEAK_THRESHOLD}]
    assert all("tooltip" in layer["encoding"] for layer in spec["layer"])
    assert spec["title"] == "OS is your weakest topic"
    assert spec["height"] == charts.ROW_PX * len(WEAKNESS)


def test_shared_theme_sets_fonts_and_drops_the_frame():
    config = charts.weakness_bars(WEAKNESS, "t").to_dict()["config"]
    assert config["font"] == "Atkinson Hyperlegible Next"
    assert config["view"]["strokeWidth"] == 0
    assert (config["title"]["font"], config["title"]["anchor"]) == ("Bricolage Grotesque", "start")
    assert config["axis"]["domain"] is False and config["axis"]["ticks"] is False
