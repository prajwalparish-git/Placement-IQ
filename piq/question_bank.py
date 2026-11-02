"""The question bank: vetted multiple-choice questions, served instantly or mixed into quizzes.

data/questions/mcq_bank.csv is the bank (its raw source, MCQ.csv, is not committed);
data/bank_topics.json maps each of its fine-grained topics to the syllabus topic it serves
(career_catalog.json), or to null. Without the CSV the bank is empty and every quiz question
is generated, as before. Questions whose
options repeat, whose answer letter is invalid or whose text repeats another's are skipped.
Pure data, no Streamlit.
"""

import csv
import json
import random
from collections.abc import Iterable
from functools import lru_cache

from pydantic import ValidationError

from piq.checks import text_hash
from piq.config import DATA_DIR, DIFFICULTIES
from piq.schemas import Question

BANK = DATA_DIR / "questions" / "mcq_bank.csv"
TOPIC_MAP = DATA_DIR / "bank_topics.json"
_LETTERS = "ABCD"


@lru_cache(maxsize=1)
def topic_map() -> dict[str, str | None]:
    """Bank topic -> syllabus topic (None: no domain teaches it)."""
    return json.loads(TOPIC_MAP.read_text(encoding="utf-8"))["topics"]


def _question(row: dict[str, str]) -> Question | None:
    options = [(row.get(f"option_{c}") or "").strip() for c in "abcd"]
    letter = (row.get("correct_option") or "").strip().upper()
    if letter not in _LETTERS or not all(options) or len({o.lower() for o in options}) < 4:
        return None
    try:
        return Question(
            text=(row.get("question") or "").strip(),
            options=options,
            correct_index=_LETTERS.index(letter),
            explanation=(row.get("explanation") or "").strip() or "From the question bank.",
            bloom_level=row.get("bloom_level") or "understand",
        )
    except ValidationError:
        return None


@lru_cache(maxsize=1)
def _questions() -> dict[tuple[str, str], tuple[Question, ...]]:
    """(syllabus topic, difficulty) -> distinct valid questions, in file order."""
    if not BANK.is_file():
        return {}
    mapping = topic_map()
    out: dict[tuple[str, str], list[Question]] = {}
    seen: set[str] = set()
    with BANK.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            topic = mapping.get((row.get("topic") or "").strip())
            difficulty = (row.get("difficulty") or "").strip().lower()
            if topic is None or difficulty not in DIFFICULTIES:
                continue
            q = _question(row)
            if q is None or (h := text_hash(q.text)) in seen:
                continue
            seen.add(h)
            out.setdefault((topic, difficulty), []).append(q)
    return {k: tuple(v) for k, v in out.items()}


def qid(q: Question) -> str:
    """A question's stable id: the critic's duplicate hash of its text (unique in the bank)."""
    return text_hash(q.text)


@lru_cache(maxsize=1)
def _by_id() -> dict[str, tuple[str, str, Question]]:
    return {qid(q): (t, d, q) for (t, d), qs in _questions().items() for q in qs}


def get(question_id: str) -> tuple[str, str, Question] | None:
    """(syllabus topic, difficulty, question) for a bank question id, or None."""
    return _by_id().get(question_id)


def counts() -> dict[str, dict[str, int]]:
    """Syllabus topic -> difficulty -> bank questions."""
    out: dict[str, dict[str, int]] = {}
    for (t, d), qs in _questions().items():
        out.setdefault(t, {})[d] = len(qs)
    return out


def available(topic: str, difficulty: str) -> int:
    """How many bank questions serve `topic` at `difficulty`."""
    return len(_questions().get((topic, difficulty), ()))


def size() -> int:
    """Questions in the bank that some syllabus topic can use."""
    return sum(len(v) for v in _questions().values())


def draw(topic: str, difficulty: str, k: int, avoid: Iterable[str], seed: str) -> list[Question]:
    """Up to `k` bank questions on `topic` at `difficulty`, none matching a text in `avoid`
    (compared like the critic's duplicate check), chosen reproducibly from `seed`."""
    if k <= 0:
        return []
    banned = {text_hash(t) for t in avoid}
    pool = [q for q in _questions().get((topic, difficulty), ()) if text_hash(q.text) not in banned]
    return random.Random(seed).sample(pool, min(k, len(pool)))


def clear_cache() -> None:
    topic_map.cache_clear()
    _questions.cache_clear()
    _by_id.cache_clear()
