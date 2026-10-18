"""Deterministic rules: weakness scoring and the zero-cost first stage of the critic.

Every `check_*` returns a list of human-readable rejection reasons; empty means approved.
The reasons are fed back verbatim into the regeneration prompt.
"""

import hashlib
import re

from piq.config import TOPICS, WEAK_MIN_SHARE, WEAK_THRESHOLD
from piq.schemas import InterviewTurn, ProfileExtraction, QuizSet, WeeklyPlan

_QUESTION_REASON = re.compile(r"^question (\d+): (.*)$", re.S)


def question_reason(index: int, message: str) -> str:
    return f"question {index}: {message}"


def question_issues(reasons: list[str]) -> dict[int, list[str]] | None:
    """index -> messages when every reason concerns a single question, else None."""
    issues: dict[int, list[str]] = {}
    for r in reasons:
        m = _QUESTION_REASON.match(r)
        if m is None:
            return None
        issues.setdefault(int(m[1]), []).append(m[2])
    return issues or None


def text_hash(text: str) -> str:
    norm = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return hashlib.sha1(norm.encode()).hexdigest()[:16]


def topic_weakness(scores: dict[str, float], missing_topics: set[str]) -> dict[str, float]:
    """0 = strong, 1 = weak. Quiz evidence wins; otherwise fall back to resume gaps."""
    out = {}
    for t in TOPICS:
        if t in scores:
            out[t] = round(1 - scores[t] / 100, 2)
        else:
            out[t] = 0.7 if t in missing_topics else 0.4
    return out


def weak_topics(weakness: dict[str, float]) -> list[str]:
    return sorted(
        (t for t, w in weakness.items() if w > WEAK_THRESHOLD), key=lambda t: -weakness[t]
    )


def check_profile(ext: ProfileExtraction, required: list[str]) -> list[str]:
    reasons = []
    if not ext.skills:
        reasons.append("skills is empty; extract every technical skill mentioned in the resume")
    allowed = {s.lower() for s in required}
    unknown = [s for s in ext.matched_skills if s.lower() not in allowed]
    if unknown:
        reasons.append(
            f"matched_skills must be chosen only from the required list; invalid: {unknown}"
        )
    return reasons


def check_plan(plan: WeeklyPlan, week_no: int, weakness: dict[str, float]) -> list[str]:
    reasons = []
    if plan.week_no != week_no:
        reasons.append(f"week_no must be {week_no}, got {plan.week_no}")
    if sorted(d.day for d in plan.days) != list(range(1, 8)):
        reasons.append("days must be numbered 1 to 7 exactly once each")
    weak = weak_topics(weakness)
    if weak:
        minutes = plan.minutes_by_topic()
        absent = [t for t in weak if t not in minutes]
        if absent:
            reasons.append(f"weak topics missing from the plan: {absent}")
        share = sum(minutes.get(t, 0) for t in weak) / sum(minutes.values())
        if share < WEAK_MIN_SHARE:
            reasons.append(
                f"weak topics {weak} get {share:.0%} of total minutes; "
                f"they must get at least {WEAK_MIN_SHARE:.0%}"
            )
        top = max((m for t, m in minutes.items() if t not in weak), default=0)
        outranked = [t for t in weak if 0 < minutes.get(t, 0) < top]
        if outranked:
            reasons.append(
                f"weak topics {outranked} get fewer minutes than a non-weak topic ({top}); "
                "every weak topic needs at least as many minutes as any other topic"
            )
    return reasons


def check_quiz(
    quiz: QuizSet, topic: str, difficulty: str, count: int, previous: list[str]
) -> list[str]:
    reasons = []
    if quiz.topic != topic:
        reasons.append(f"topic must be {topic}, got {quiz.topic}")
    if quiz.difficulty != difficulty:
        reasons.append(f"difficulty must be {difficulty}, got {quiz.difficulty}")
    if len(quiz.questions) != count:
        reasons.append(f"exactly {count} questions required, got {len(quiz.questions)}")
    seen = {text_hash(t) for t in previous}
    for i, q in enumerate(quiz.questions):
        if len({o.strip().lower() for o in q.options}) < 4:
            reasons.append(question_reason(i, "options are not distinct"))
        h = text_hash(q.text)
        if h in seen:
            reasons.append(
                question_reason(i, f"duplicate of an earlier question ({q.text[:60]!r})")
            )
        seen.add(h)
    return reasons


def check_turn(turn: InterviewTurn, asked: list[str]) -> list[str]:
    reasons = []
    if turn.question.count("?") > 2:
        reasons.append("ask exactly one question per turn")
    if text_hash(turn.question) in {text_hash(q) for q in asked}:
        reasons.append(f"question already asked: {turn.question[:80]!r}")
    return reasons
