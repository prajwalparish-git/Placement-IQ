"""Settings loaded once from the environment / .env file."""

import os
import re
from dataclasses import dataclass
from datetime import time
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "evaluation" / "results"
STATIC_DIR = ROOT / "static"  # served at app/static/: fonts, brand, app.css
BRAND_DIR = STATIC_DIR / "brand"  # mark.svg (icon) and wordmark.svg

# The computer-science core syllabus. Every domain's own topics (and which of them are always
# tracked) live in data/career_catalog.json and are read by piq/syllabus.py; these six stay
# the CS core, which the frozen evaluation and the demo seed are built on.
TOPICS = ("Aptitude", "DBMS", "OS", "CN", "DSA", "OOP")
DEFAULT_DOMAIN = "cs"  # the domain of a role the catalog does not list (the original CS roles)
DEFAULT_SAMPLE = "data_analyst.txt"  # the sample Home's "Try it with a sample resume" opens
USN_RE = re.compile(r"^[A-Z0-9]{4,20}$")  # a student's USN, upper-cased: 4-20 letters/digits
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DB_CONNECT_TIMEOUT = 3  # seconds to wait for PostgreSQL before the telemetry layer uses SQLite
VOICE_RUBRIC_MAX = 15  # a voice interview's rubric score runs 0 to 15
VOICE_CRITERION_MAX = 5  # verbal clarity and relevance each run 0 to 5
MAX_DOMAIN_TOPICS = 10  # one topic colour each; tests/test_syllabus.py enforces it
DIFFICULTIES = ("easy", "medium", "hard")
INTERVIEW_TYPES = ("HR", "Technical", "Project")  # generic types; the frozen evaluation uses them
INSTANT_QUIZ_SIZE = 5  # questions in a quiz served straight from the question bank
BULLET_MAX_CHARS = 400  # a resume bullet sent for an XYZ rewrite

QUIZ_SIZE = 5  # questions per topic when a quiz is first set up
QUIZ_MAX_PER_TOPIC = 50
QUIZ_MAX_TOTAL = 100
QUIZ_BATCH = 10  # questions per generation call; each batch is checked by the critic
# Share of each quiz part (one topic at one difficulty) drawn from the local question bank
# (piq/question_bank.py) when it has unseen questions; the LLM writes the rest, through the
# critic. Half keeps the critic visible on every quiz while halving its token cost.
QUIZ_BANK_SHARE = 0.5
DEFAULT_MIX = {"easy": (60, 90), "medium": (20, 80), "hard": (10, 40)}  # slider handles per level
RESUME_REVIEW_DAYS = 14  # a resume version this old is due for review
RESUME_MAX_EDUCATION = 6  # education entries a resume can list (Class 10 to a doctorate)
RESUME_MAX_EXPERIENCE = 8  # jobs, internships and other work a resume can list
# Kinds of work; every kind but an internship counts towards years of experience.
EXPERIENCE_TYPES = (
    "Full-time",
    "Internship",
    "Part-time",
    "Contract",
    "Freelance",
    "Apprenticeship",
)
RESUME_MASTERY_AT = 70  # recent quiz average (%) at which a topic's skills belong on the resume
PROJECT_STATUSES = ("Idea", "In progress", "Done")
INTERVIEW_MAX_TURNS = 5
CRITERION_WEAK_BELOW = 3.0  # an interview criterion averaging below this gets a tip
# One fixed tip per rubric criterion (the evaluator's four), shown when it averages low.
INTERVIEW_TIPS = {
    "relevance": "Answer the question that was asked in your first sentence, then add detail.",
    "depth": "Add specifics: a number, a tool, a trade-off you weighed or the result you got.",
    "structure": (
        "Use STAR for behavioural answers (situation, task, action, result); for technical "
        "ones, define the idea, explain how it works, then give an example."
    ),
    "clarity": "Use short sentences with one idea each, and end by restating your main point.",
}
# Readiness weighs a required skill practised under a syllabus topic (role_skills.json maps it to
# a topic) this many times a tool skill (mapped to null): the topics are what recruitment tests
# examine, a tool is learnt in days.
SYLLABUS_SKILL_WEIGHT = 2
WEAK_THRESHOLD = 0.5  # weakness above this marks a topic as weak
WEAK_MIN_SHARE = 0.5  # weak topics must get at least this share of weekly minutes
DIFFICULTY_UP_AT = 80  # a quiz score (%) at or above this suggests the next difficulty up
DIFFICULTY_DOWN_BELOW = 50  # a score below this suggests the next difficulty down
TREND_STEP = 10  # points the latest quiz must beat (or miss) the ones before by to count as a trend
RESUME_MAX_PDF_PAGES = 30  # pages read from a PDF resume; the rest is ignored
RESUME_MAX_DOCX_UNZIPPED = 25 * 1024 * 1024  # bytes a DOCX may unpack to (zip-bomb guard)
TIMEZONE = "Asia/Kolkata"  # students' local time, for dates shown in the app
STUDY_TIME = time(19, 0)  # default daily start of an exported plan's calendar events
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

# Topic colours by position: a domain's n-th topic (career_catalog.json) takes the n-th colour,
# so a topic keeps its colour on every page. The first six are Okabe-Ito hues without yellow;
# the last four (purple, olive, rose, violet) were chosen to stay as far from all others as the
# contrast rule allows. Lightness is tuned per scheme to >= 3:1 on the background. They mark
# chart series and topic chips (which also show the topic name), never a status.
TOPIC_PALETTE = {
    "light": (
        "#C78100",
        "#005D9C",
        "#A55582",
        "#009B71",
        "#B23D00",
        "#3799CC",
        "#672692",
        "#7A710D",
        "#6C3C4B",
        "#7858BB",
    ),
    "dark": (
        "#EFA71C",
        "#0975B6",
        "#DF8BB9",
        "#009B71",
        "#D05900",
        "#55B4E8",
        "#A365D4",
        "#A09520",
        "#D35182",
        "#B495FE",
    ),
}

# Quiz outcomes in result charts. Vega cannot follow the theme switch, so each reads at >= 3:1
# on both page backgrounds; the charts also name every outcome in words (legend, tooltip).
OUTCOME_COLORS = {"Correct": BRAND_COLOR, "Wrong": "#CF4B5B", "Skipped": "#8E8A80"}  # warm grey


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    groq_api_key: str  # the first key of the pool (scripts/check_models.py checks it)
    model_large: str
    model_small: str
    db_path: Path
    max_critic_retries: int
    mock_mode: bool
    seed_demo: bool = False  # recreate the demo student on start when the DB is empty
    # GROQ_API_KEY_1 (interactive lane) and GROQ_API_KEY_2 (background lane); GROQ_API_KEY alone
    # still works as a one-key pool. See piq/llm.py for the lanes and failover.
    groq_api_keys: tuple[str, ...] = ()
    # Telemetry layer (database/): PostgreSQL when DATABASE_URL answers, else this SQLite file.
    database_url: str = ""
    telemetry_db_path: Path = DATA_DIR / "placement_nexus.db"


def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes"}


@lru_cache
def settings() -> Settings:
    # PIQ_DOTENV lets tests point at a non-existent file so the developer's .env never leaks in.
    load_dotenv(os.getenv("PIQ_DOTENV", ROOT / ".env"))
    pool = tuple(
        dict.fromkeys(
            k
            for k in (os.getenv("GROQ_API_KEY_1", ""), os.getenv("GROQ_API_KEY_2", ""))
            if k.strip()
        )
    ) or tuple(k for k in (os.getenv("GROQ_API_KEY", ""),) if k.strip())
    s = Settings(
        groq_api_key=pool[0] if pool else "",
        groq_api_keys=pool,
        model_large=os.getenv("GROQ_MODEL_LARGE", ""),
        model_small=os.getenv("GROQ_MODEL_SMALL", ""),
        db_path=Path(os.getenv("DB_PATH", str(DATA_DIR / "placementiq.db"))),
        max_critic_retries=int(os.getenv("MAX_CRITIC_RETRIES", "2")),
        mock_mode=_flag("MOCK_MODE", "true"),
        seed_demo=_flag("SEED_DEMO", "false"),
        database_url=os.getenv("DATABASE_URL", "").strip(),
        telemetry_db_path=Path(
            os.getenv("TELEMETRY_DB_PATH", str(DATA_DIR / "placement_nexus.db"))
        ),
    )
    if not s.mock_mode:
        missing = [
            k
            for k, v in {
                "GROQ_API_KEY_1 (or GROQ_API_KEY)": s.groq_api_key,
                "GROQ_MODEL_LARGE": s.model_large,
                "GROQ_MODEL_SMALL": s.model_small,
            }.items()
            if not v
        ]
        if missing:
            raise ConfigError(f"MOCK_MODE=false but {', '.join(missing)} not set in .env")
    return s
