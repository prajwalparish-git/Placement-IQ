"""Settings loaded once from the environment / .env file."""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "evaluation" / "results"

TOPICS = ("Aptitude", "DBMS", "OS", "CN", "DSA", "OOP")
DIFFICULTIES = ("easy", "medium", "hard")
INTERVIEW_TYPES = ("HR", "Technical", "Project")

QUIZ_SIZE = 5
INTERVIEW_MAX_TURNS = 5
WEAK_THRESHOLD = 0.5  # weakness above this marks a topic as weak
WEAK_MIN_SHARE = 0.5  # weak topics must get at least this share of weekly minutes


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
