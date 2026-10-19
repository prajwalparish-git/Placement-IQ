"""Design tokens: .streamlit/config.toml agrees with piq.config, and every colour pair meets
its contrast and distinctness rule in both schemes."""

import itertools
import math
import re
import tomllib

import pytest

from piq.config import (
    BRAND_COLOR,
    BRAND_DIR,
    PALETTE,
    ROOT,
    SCHEMES,
    SEMANTIC_COLORS,
    TOPIC_COLORS,
    TOPICS,
)

THEME = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))["theme"]
ALERT_ALPHA = {"light": 0.10, "dark": 0.20}  # Streamlit's alert tint over the background
# Old accent vs Aptitude (rejected at Checkpoint A) measured 0.038 / 0.023: they must fail this.
MIN_STATUS_DISTANCE = 0.08
MIN_TOPIC_DISTANCE = 0.10


def _rgb(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))


def _linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def contrast(a: str, b: str) -> float:
    """WCAG 2 contrast ratio."""
    la, lb = (
        sum(w * _linear(c) for w, c in zip((0.2126, 0.7152, 0.0722), _rgb(x), strict=True))
        for x in (a, b)
    )
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def oklab(hex_color: str) -> tuple[float, float, float]:
    r, g, b = (_linear(c) for c in _rgb(hex_color))
    lms = (
        0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b,
        0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b,
        0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b,
    )
    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in lms)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def distance(a: str, b: str) -> float:
    """Perceptual distance: Euclidean in OKLab (about 0.02 is just noticeable)."""
    return math.dist(oklab(a), oklab(b))


def tint(color: str, under: str, alpha: float) -> str:
    mixed = (x * alpha + y * (1 - alpha) for x, y in zip(_rgb(color), _rgb(under), strict=True))
    return "#" + "".join(f"{round(c * 255):02X}" for c in mixed)


ROLE_KEYS = {"success": "green", "warning": "yellow", "error": "red", "info": "blue"}


@pytest.mark.parametrize("scheme", SCHEMES)
def test_config_toml_mirrors_the_tokens(scheme):
    t, p, s = THEME[scheme], PALETTE[scheme], SEMANTIC_COLORS[scheme]
    assert (t["backgroundColor"], t["secondaryBackgroundColor"]) == (p["background"], p["surface"])
    assert (t["textColor"], t["linkColor"], t["borderColor"]) == (
        p["text"],
        p["primary_text"],
        p["border"],
    )
    assert (t["primaryColor"], t["dataframeBorderColor"]) == (p["primary"], p["hairline"])
    for role, key in ROLE_KEYS.items():
        assert t[f"{key}Color"] == t[f"{key}TextColor"] == s[role]
    assert t["chartCategoricalColors"] == [TOPIC_COLORS[scheme][topic] for topic in TOPICS]
    side = THEME[scheme]["sidebar"]
    assert (side["backgroundColor"], side["secondaryBackgroundColor"]) == (
        p["surface"],
        p["background"],
    )
    assert (side["textColor"], side["primaryColor"]) == (p["text"], p["primary"])


@pytest.mark.parametrize("scheme", SCHEMES)
def test_text_reaches_4_5_to_1_on_every_layer(scheme):
    p = PALETTE[scheme]
    texts = [p["text"], p["muted"], p["primary_text"], *SEMANTIC_COLORS[scheme].values()]
    for text, layer in itertools.product(texts, (p["background"], p["surface"])):
        assert contrast(text, layer) >= 4.5, (text, layer)


@pytest.mark.parametrize("scheme", SCHEMES)
def test_alert_text_reaches_4_5_to_1_on_its_tint(scheme):
    p = PALETTE[scheme]
    for color, layer in itertools.product(
        SEMANTIC_COLORS[scheme].values(), (p["background"], p["surface"])
    ):
        assert contrast(color, tint(color, layer, ALERT_ALPHA[scheme])) >= 4.5, (color, layer)


@pytest.mark.parametrize("scheme", SCHEMES)
def test_buttons_edges_and_chart_marks_reach_3_to_1(scheme):
    p = PALETTE[scheme]
    assert contrast("#FFFFFF", p["primary"]) >= 4.5  # white primary-button label
    for mark in (p["primary"], p["border"]):
        assert contrast(mark, p["background"]) >= 3 and contrast(mark, p["surface"]) >= 3
    for topic, color in TOPIC_COLORS[scheme].items():
        assert contrast(color, p["background"]) >= 3, topic


@pytest.mark.parametrize("scheme", SCHEMES)
def test_every_topic_has_its_own_colour(scheme):
    colors = TOPIC_COLORS[scheme]
    assert list(colors) == list(TOPICS)
    for (a, ca), (b, cb) in itertools.combinations(colors.items(), 2):
        assert distance(ca, cb) >= MIN_TOPIC_DISTANCE, (a, b)


@pytest.mark.parametrize("scheme", SCHEMES)
def test_status_and_primary_colours_stay_away_from_topic_colours(scheme):
    p = PALETTE[scheme]
    others = {**SEMANTIC_COLORS[scheme], "primary": p["primary"], "primary_text": p["primary_text"]}
    for (role, color), (topic, tc) in itertools.product(
        others.items(), TOPIC_COLORS[scheme].items()
    ):
        assert distance(color, tc) >= MIN_STATUS_DISTANCE, (role, topic, distance(color, tc))


def test_the_threshold_rejects_the_old_amber_accent():
    assert distance("#B7791F", TOPIC_COLORS["light"]["Aptitude"]) < MIN_STATUS_DISTANCE
    assert distance("#E8AE45", TOPIC_COLORS["dark"]["Aptitude"]) < MIN_STATUS_DISTANCE


def test_fonts_are_self_hosted_woff2_files_with_their_licences():
    faces = THEME["fontFaces"]
    families = {f["family"] for f in faces}
    assert families == {"Atkinson Hyperlegible Next", "Bricolage Grotesque", "JetBrains Mono"}
    total = 0
    for face in faces:
        assert face["url"].startswith("app/static/fonts/")  # served by the app, no CDN
        path = ROOT / "static" / face["url"].removeprefix("app/static/")
        data = path.read_bytes()
        assert data[:4] == b"wOF2", path
        assert "SIL OPEN FONT LICENSE" in (path.parent / "OFL.txt").read_text(encoding="utf-8")
        total += len(data)
    assert total < 300 * 1024
    for key in ("font", "headingFont", "codeFont"):
        assert "://" not in THEME[key]
        assert THEME[key].split(",")[0].strip() in families


def test_type_scale_keeps_text_legible_at_a_distance():
    def px(size: str) -> float:
        return float(size.removesuffix("rem")) * THEME["baseFontSize"]

    assert THEME["baseFontSize"] >= 16  # body
    sizes = [px(s) for s in THEME["headingFontSizes"]]
    assert sizes[:3] == [36, 24, 18] and min(sizes) >= 14
    assert px(THEME["codeFontSize"]) >= 14 and px(THEME["metricValueFontSize"]) == 36


@pytest.mark.parametrize("scheme", SCHEMES)
def test_sequential_ramp_runs_away_from_the_background(scheme):
    ramp = THEME[scheme]["chartSequentialColors"]
    steps = [contrast(c, PALETTE[scheme]["background"]) for c in ramp]
    assert len(ramp) == 10 and steps == sorted(steps) and steps[-1] >= 4.5


CSS = (ROOT / "static" / "app.css").read_text(encoding="utf-8")


def _selectors(group: str) -> list[str]:
    """Split a selector list on top-level commas (not those inside :is(...) or :has(...))."""
    parts, depth, current = [], 0, ""
    for ch in group:
        depth += {"(": 1, ")": -1}.get(ch, 0)
        if ch == "," and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += ch
    return [*parts, current.strip()]


def test_stylesheet_is_small_and_targets_only_data_testids():
    assert len(CSS.splitlines()) < 150 and len(CSS.encode()) < 8 * 1024
    assert "st-emotion-cache" not in CSS
    rules = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
    for group in re.findall(r"([^{}]+)\{", rules):
        if group.strip().startswith("@"):
            continue
        for selector in _selectors(group):
            assert '[data-testid="' in selector, selector
    tokens = {c.upper() for scheme in PALETTE.values() for c in scheme.values()}
    assert {c.upper() for c in re.findall(r"#[0-9A-Fa-f]{6}", rules)} <= tokens


@pytest.mark.parametrize("name", ["mark.svg", "wordmark.svg"])
def test_brand_svgs_are_self_contained_and_on_palette(name):
    import xml.etree.ElementTree as ET

    text = (BRAND_DIR / name).read_text(encoding="utf-8")
    root = ET.fromstring(text)
    ns = "{http://www.w3.org/2000/svg}"
    assert root.find(f"{ns}title").text == "PlacementIQ"  # accessible name
    assert root.find(f".//{ns}text") is None  # lettering is outlined: no font needed in <img>
    assert "href" not in text and "url(" not in text  # nothing fetched from elsewhere
    assert BRAND_COLOR in text


def test_brand_colour_reads_on_every_background():
    for scheme in SCHEMES:
        for layer in ("background", "surface"):
            assert contrast(BRAND_COLOR, PALETTE[scheme][layer]) >= 3, (scheme, layer)
        for tc in TOPIC_COLORS[scheme].values():
            assert distance(BRAND_COLOR, tc) >= MIN_STATUS_DISTANCE
