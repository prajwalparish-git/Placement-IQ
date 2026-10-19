"""Settings loaded once from the environment / .env file."""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "evaluation" / "results"
STATIC_DIR = ROOT / "static"  # served at app/static/: fonts, brand, app.css
BRAND_DIR = STATIC_DIR / "brand"  # mark.svg (icon) and wordmark.svg

TOPICS = ("Aptitude", "DBMS", "OS", "CN", "DSA", "OOP")
DIFFICULTIES = ("easy", "medium", "hard")
INTERVIEW_TYPES = ("HR", "Technical", "Project")

QUIZ_SIZE = 5
INTERVIEW_MAX_TURNS = 5
WEAK_THRESHOLD = 0.5  # weakness above this marks a topic as weak
WEAK_MIN_SHARE = 0.5  # weak topics must get at least this share of weekly minutes
DIFFICULTY_UP_AT = 80  # a quiz score (%) at or above this suggests the next difficulty up
DIFFICULTY_DOWN_BELOW = 50  # a score below this suggests the next difficulty down
RESUME_MAX_PDF_PAGES = 30  # pages read from a PDF resume; the rest is ignored
RESUME_MAX_DOCX_UNZIPPED = 25 * 1024 * 1024  # bytes a DOCX may unpack to (zip-bomb guard)
TIMEZONE = "Asia/Kolkata"  # students' local time, for dates shown in the app
RECENT_DAYS = 7  # a topic quizzed within this many days counts as practised; a plan
# this old is due for next week's version

# --- design tokens: the UI's colours ------------------------------------------------
# .streamlit/config.toml mirrors these (Streamlit reads only TOML); tests/test_theme.py
# checks contrast and that both files agree. See docs/design/DESIGN.md.
SCHEMES = ("light", "dark")

PALETTE = {
    "light": {
        "background": "#FBFBFA",  # page
        "surface": "#F0F2F0",  # sidebar, inputs, table headers
        "text": "#1A2326",
        "muted": "#566461",  # captions and secondary text
        "border": "#7A8582",  # input and card edges, >= 3:1
        "hairline": "#DCE1DE",  # table rules only (decorative)
        "primary": "#0D6670",  # actions; also today's focus and streaks, always with an icon
        "primary_text": "#0D6670",  # links and teal text, >= 4.5:1
    },
    "dark": {
        "background": "#111A1C",
        "surface": "#1A2528",
        "text": "#E3EAE8",
        "muted": "#A0AEAB",
        "border": "#64716E",
        "hairline": "#2C383B",
        "primary": "#1F7F86",
        "primary_text": "#6CCBC4",
    },
}

# Logo teal (static/brand/*.svg): an <img> cannot follow the theme toggle, so one tone that
# reads on both sidebars and both page backgrounds (>= 3:1 on each).
BRAND_COLOR = "#278C93"

# Status colours: always shown with an icon and words, never used for a topic.
SEMANTIC_COLORS = {
    "light": {"success": "#1B6F36", "warning": "#784E00", "error": "#951B2C", "info": "#0045D2"},
    "dark": {"success": "#5BBF7A", "warning": "#F0D45C", "error": "#FF8675", "info": "#A9BCF5"},
}

# Okabe-Ito hues without yellow, lightness-tuned per scheme to >= 3:1 on the background.
# They mark chart series and topic chips (which also show the topic name), never a status.
TOPIC_COLORS = {
    "light": {
        "Aptitude": "#C78100",
        "DBMS": "#005D9C",
        "OS": "#A55582",
        "CN": "#009B71",
        "DSA": "#B23D00",
        "OOP": "#3799CC",
    },
    "dark": {
        "Aptitude": "#EFA71C",
        "DBMS": "#0975B6",
        "OS": "#DF8BB9",
        "CN": "#009B71",
        "DSA": "#D05900",
        "OOP": "#55B4E8",
    },
}


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    groq_api_key: str
    model_large: str
    model_small: str
    db_path: Path
    max_critic_retries: int
    mock_mode: bool
    seed_demo: bool = False  # recreate the demo student on start when the DB is empty


def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes"}


@lru_cache
def settings() -> Settings:
    # PIQ_DOTENV lets tests point at a non-existent file so the developer's .env never leaks in.
    load_dotenv(os.getenv("PIQ_DOTENV", ROOT / ".env"))
    s = Settings(
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        model_large=os.getenv("GROQ_MODEL_LARGE", ""),
        model_small=os.getenv("GROQ_MODEL_SMALL", ""),
        db_path=Path(os.getenv("DB_PATH", str(DATA_DIR / "placementiq.db"))),
        max_critic_retries=int(os.getenv("MAX_CRITIC_RETRIES", "2")),
        mock_mode=_flag("MOCK_MODE", "true"),
        seed_demo=_flag("SEED_DEMO", "false"),
    )
    if not s.mock_mode:
        missing = [
            k
            for k, v in {
                "GROQ_API_KEY": s.groq_api_key,
                "GROQ_MODEL_LARGE": s.model_large,
                "GROQ_MODEL_SMALL": s.model_small,
            }.items()
            if not v
        ]
        if missing:
            raise ConfigError(f"MOCK_MODE=false but {', '.join(missing)} not set in .env")
    return s
