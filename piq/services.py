"""Controllers: every operation the UI performs, as plain functions over agents + db.

Views call these (plus formatter and ui) and nothing below them. Each function validates
its input, runs the agents, persists the result and returns typed state, so every user
flow is testable without Streamlit. `ServiceError` messages are safe to show to users.
"""

import json
import re
import sqlite3
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from pydantic import BaseModel

from piq import agents, checks, db
from piq.config import (
    DATA_DIR,
    DIFFICULTIES,
    INTERVIEW_TYPES,
    RECENT_DAYS,
    RESULTS_DIR,
    TOPICS,
    WEAK_THRESHOLD,
)
from piq.graph import OnEvent
from piq.resume import extract_text
from piq.schemas import AnswerEvaluation, InterviewTurn, QuizSet, StudentProfile, WeeklyPlan

USN_RE = re.compile(r"^[A-Z0-9]{4,20}$")
SAMPLES_DIR = DATA_DIR / "sample_resumes"
MAX_ANSWER_CHARS = 4000


class ServiceError(ValueError):
    """Invalid input or state for the requested operation."""


def _require_profile(student_id: str | None) -> StudentProfile:
    profile = current_profile(student_id)
    if profile is None:
        raise ServiceError("Onboard this student first.")
    return profile


# --- students & onboarding -----------------------------------------------------


def normalise_usn(usn: str | None) -> str:
    usn = (usn or "").strip().upper()
    if not USN_RE.match(usn):
        raise ServiceError("USN is required: 4-20 letters/digits, no spaces.")
    return usn


def list_students() -> list[sqlite3.Row]:
    return db.list_students()


def current_profile(student_id: str | None) -> StudentProfile | None:
    return db.latest_profile(student_id) if student_id else None


def target_roles() -> list[str]:
    return list(agents.roles())


@lru_cache(maxsize=1)
def sample_resumes() -> tuple[str, ...]:
    """The bundled sample files; they ship with the app, so the folder is listed once."""
    return tuple(sorted(p.name for p in SAMPLES_DIR.glob("*.txt")))


def load_sample(name: str) -> str:
    if name not in sample_resumes():  # also blocks path traversal: only listed files load
        raise ServiceError(f"Unknown sample resume {name!r}.")
    return (SAMPLES_DIR / name).read_text(encoding="utf-8")


def read_resume(filename: str, data: bytes) -> str:
    """Uploaded file -> text; raises resume.ResumeError (a ValueError) with a user message."""
    return extract_text(filename, data)


def onboard(
    usn: str, target_role: str, resume_text: str, on_event: OnEvent | None = None
) -> tuple[str, StudentProfile]:
    usn = normalise_usn(usn)
    if target_role not in agents.roles():
        raise ServiceError(f"Unknown target role {target_role!r}.")
    if not resume_text.strip():
        raise ServiceError("The resume is empty.")
    profile = agents.create_profile(resume_text, target_role, on_event)
    return db.save_profile(usn, profile), profile


# --- weekly plan ---------------------------------------------------------------


@dataclass(frozen=True)
class PlanOverview:
    plans: list[WeeklyPlan]
    scores: dict[str, float]
    weakness: dict[str, float]
    next_week: int


def plan_overview(student_id: str, profile: StudentProfile | None = None) -> PlanOverview:
    """`profile`: the student's current profile when the caller already loaded it."""
    profile = profile or _require_profile(student_id)
    plans = db.list_plans(student_id)
    scores = db.topic_performance(student_id)
    return PlanOverview(
        plans=plans,
        scores=scores,
        weakness=checks.topic_weakness(scores, agents.missing_topics(profile)),
        next_week=plans[-1].week_no + 1 if plans else 1,
    )


def generate_next_plan(student_id: str, on_event: OnEvent | None = None) -> WeeklyPlan:
    profile = _require_profile(student_id)
    ov = plan_overview(student_id, profile)
    previous = ov.plans[-1] if ov.plans else None
    plan = agents.plan_week(profile, ov.scores, ov.next_week, previous, student_id, on_event)
    db.save_plan(student_id, plan)
    return plan


# --- quizzes -------------------------------------------------------------------


@dataclass(frozen=True)
class QuizResult:
    quiz: QuizSet
    chosen: list[int | None]
    score_pct: float
    next_difficulty: str


def _check_quiz_params(topic: str, difficulty: str | None = None) -> None:
    if topic not in TOPICS:
        raise ServiceError(f"Unknown topic {topic!r}.")
    if difficulty is not None and difficulty not in DIFFICULTIES:
        raise ServiceError(f"Unknown difficulty {difficulty!r}.")


def suggested_difficulty(student_id: str, topic: str) -> str:
    _check_quiz_params(topic)
    last = db.last_attempt(student_id, topic)
    if last is None:
        return "medium"
    return agents.suggest_difficulty(last["score_pct"], last["difficulty"])


def start_quiz(
    student_id: str, topic: str, difficulty: str, on_event: OnEvent | None = None
) -> QuizSet:
    _require_profile(student_id)
    _check_quiz_params(topic, difficulty)
    previous = db.asked_questions(student_id, topic)
    return agents.make_quiz(topic, difficulty, previous, student_id=student_id, on_event=on_event)


def submit_quiz(student_id: str, quiz: QuizSet, chosen: list[int | None]) -> QuizResult:
    if len(chosen) != len(quiz.questions):
        raise ServiceError("The answers do not match the quiz.")
    if any(a is not None and a not in range(4) for a in chosen):
        raise ServiceError("Invalid answer choice.")
    pct = db.save_quiz_attempt(student_id, quiz, list(chosen))
    return QuizResult(quiz, list(chosen), pct, agents.suggest_difficulty(pct, quiz.difficulty))


# --- interviews ----------------------------------------------------------------


class AnsweredTurn(BaseModel):
    question: str
    answer: str
    evaluation: AnswerEvaluation


class InterviewSession(BaseModel):
    """Typed state of one mock interview, kept in st.session_state between reruns.

    `current` is the question awaiting an answer. It is None after an answer is saved
    until `continue_interview` succeeds, so a failed follow-up can be retried without
    re-answering (and without saving the same turn twice).
    """

    session_id: str
    interview_type: str
    past: list[dict]  # earlier sessions' Q/A: the interviewer's memory
    history: list[AnsweredTurn] = []
    current: InterviewTurn | None = None
    done: bool = False

    @property
    def average(self) -> float | None:
        if not self.history:
            return None
        return round(sum(t.evaluation.overall for t in self.history) / len(self.history), 2)

    def qa(self) -> list[dict]:
        return [{"question": t.question, "answer": t.answer} for t in self.history]


def start_interview(
    student_id: str, interview_type: str, on_event: OnEvent | None = None
) -> InterviewSession:
    profile = _require_profile(student_id)
    if interview_type not in INTERVIEW_TYPES:
        raise ServiceError(f"Unknown interview type {interview_type!r}.")
    session_id = uuid.uuid4().hex
    past = db.past_turns(student_id, exclude_session=session_id)
    first = agents.next_question(profile, interview_type, [], past, student_id, on_event)
    return InterviewSession(
        session_id=session_id, interview_type=interview_type, past=past, current=first
    )


def answer_question(student_id: str, session: InterviewSession, answer: str) -> InterviewSession:
    """Evaluate and save the answer to `session.current`; returns state with current=None."""
    if session.done or session.current is None:
        raise ServiceError("There is no open question in this session.")
    answer = (answer or "").strip()
    if not answer:
        raise ServiceError("Type an answer first.")
    if len(answer) > MAX_ANSWER_CHARS:
        raise ServiceError(f"Answers are limited to {MAX_ANSWER_CHARS} characters.")
    profile = _require_profile(student_id)
    q = session.current.question
    ev = agents.evaluate_answer(profile, session.interview_type, q, answer, student_id)
    db.save_turn(student_id, session.session_id, session.interview_type, q, answer, ev)
    return session.model_copy(
        update={
            "history": [*session.history, AnsweredTurn(question=q, answer=answer, evaluation=ev)],
            "current": None,
            "done": session.current.is_final,
        }
    )


def continue_interview(
    student_id: str, session: InterviewSession, on_event: OnEvent | None = None
) -> InterviewSession:
    """Ask the next question after an answered turn."""
    if session.done or session.current is not None:
        raise ServiceError("This session is not waiting for a new question.")
    profile = _require_profile(student_id)
    nxt = agents.next_question(
        profile, session.interview_type, session.qa(), session.past, student_id, on_event
    )
    return session.model_copy(update={"current": nxt})


# --- dashboard -----------------------------------------------------------------


@dataclass(frozen=True)
class Dashboard:
    profile: StudentProfile
    quiz_history: list[sqlite3.Row]
    plans: list[WeeklyPlan]
    sessions: list[sqlite3.Row]
    agent_stats: list[sqlite3.Row]
    rejections: list[sqlite3.Row]


def dashboard(student_id: str, profile: StudentProfile | None = None) -> Dashboard:
    """`profile`: the student's current profile when the caller already loaded it."""
    return Dashboard(
        profile=profile or _require_profile(student_id),
        quiz_history=db.quiz_history(student_id),
        plans=db.list_plans(student_id),
        sessions=db.interview_history(student_id),
        agent_stats=db.agent_stats(),
        rejections=db.recent_rejections(),
    )


# --- evaluation ----------------------------------------------------------------


def evaluation_summary() -> dict | None:
    """The last run_eval summary, or None if there is none (or it is unreadable)."""
    try:
        return json.loads((RESULTS_DIR / "summary.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# --- home: today's focus ----------------------------------------------------------


@dataclass(frozen=True)
class NextAction:
    """Today's focus: one next step chosen by rules (no LLM), why, and where to do it."""

    label: str  # the step, e.g. "Take a medium OS quiz"
    reason: str  # one plain sentence
    cta: str  # what the button does, e.g. "Open Weekly plan"
    page: str  # the view that does it
    icon: str  # Material Symbols name
    topic: str | None = None  # preselected on the Quiz page
    difficulty: str | None = None


@dataclass(frozen=True)
class ChecklistItem:
    label: str
    done: bool


@dataclass(frozen=True)
class Activity:
    at: datetime  # UTC
    text: str  # plain words built from topics, numbers and fixed vocabulary
    topic: str | None = None


@dataclass(frozen=True)
class HomeOverview:
    profile: StudentProfile
    weakness: dict[str, float]
    next_action: NextAction
    checklist: list[ChecklistItem]
    recent: list[Activity]


def utc(timestamp: str) -> datetime:
    """A SQLite CURRENT_TIMESTAMP string (UTC, no zone) as an aware datetime."""
    return datetime.fromisoformat(timestamp).replace(tzinfo=UTC)


def _article(word: str) -> str:
    return "an" if word[:1] in "aeiou" else "a"


def _difficulty_after(last: Mapping | None) -> str:
    return agents.suggest_difficulty(last["score_pct"], last["difficulty"]) if last else "medium"


def decide_next_action(
    profile: StudentProfile | None,
    latest_plan: Mapping | None,
    weakness: Mapping[str, float],
    attempts: Sequence[Mapping],
    sessions: int,
    now: datetime,
) -> NextAction:
    """The next step of the loop profile -> plan -> quiz -> adapt, first match wins:
    no profile; no plan; a weak topic not quizzed lately (weakest first); no interview yet;
    a plan at least RECENT_DAYS old with new scores since; else practise the weakest topic.
    `attempts` are quiz_history rows, oldest first."""
    if profile is None:
        return NextAction(
            "Onboard with your resume",
            "PlacementIQ starts from your resume: it finds the skills your target role needs.",
            "Open Onboard",
            "views/onboard.py",
            "upload_file",
        )
    if latest_plan is None:
        return NextAction(
            "Generate your week 1 plan",
            "A plan turns your weakest topics into seven days of practice.",
            "Open Weekly plan",
            "views/plan.py",
            "calendar_month",
        )
    last = {a["topic"]: a for a in attempts}  # oldest first, so the latest one wins
    cutoff = now - timedelta(days=RECENT_DAYS)
    for topic in sorted(weakness, key=lambda t: -weakness[t]):
        if weakness[topic] <= WEAK_THRESHOLD:
            break
        if topic not in last or utc(last[topic]["attempted_at"]) < cutoff:
            difficulty = _difficulty_after(last.get(topic))
            why = (
                "you have not taken a quiz on it yet"
                if topic not in last
                else f"it has had no quiz in the last {RECENT_DAYS} days"
            )
            return NextAction(
                f"Take {_article(difficulty)} {difficulty} {topic} quiz",
                f"{topic} is one of your weak topics and {why}.",
                "Set up this quiz",
                "views/quiz.py",
                "quiz",
                topic,
                difficulty,
            )
    if sessions == 0:
        return NextAction(
            "Try a mock interview",
            "Interviews test explaining what you know; you get feedback on every answer.",
            "Open Mock interview",
            "views/interview.py",
            "record_voice_over",
        )
    planned = utc(latest_plan["created_at"])
    since = sum(1 for a in attempts if utc(a["attempted_at"]) > planned)
    if planned <= cutoff and since:
        week = latest_plan["week_no"]
        scores = f"{since} quiz score{'s' if since != 1 else ''}"
        return NextAction(
            f"Generate your week {week + 1} plan",
            f"Your week {week} plan is {(now - planned).days} days old and {scores} came in "
            "since; the planner moves minutes to the topics that need them.",
            "Open Weekly plan",
            "views/plan.py",
            "calendar_month",
        )
    topic = max(weakness, key=lambda t: weakness[t])
    difficulty = _difficulty_after(last.get(topic))
    return NextAction(
        f"Practise {topic} with {_article(difficulty)} {difficulty} quiz",
        f"{topic} is your weakest topic; another quiz shows whether it is improving.",
        "Set up this quiz",
        "views/quiz.py",
        "quiz",
        topic,
        difficulty,
    )


def _checklist(
    profile: StudentProfile | None, latest_plan: Mapping | None, quizzes: int, sessions: int
) -> list[ChecklistItem]:
    return [
        ChecklistItem("Onboard with a resume", profile is not None),
        ChecklistItem("Generate a weekly plan", latest_plan is not None),
        ChecklistItem("Take a quiz", quizzes > 0),
        ChecklistItem("Try a mock interview", sessions > 0),
    ]


def _recent(
    latest_plan: Mapping | None, attempts: Sequence[Mapping], sessions: Sequence[Mapping]
) -> list[Activity]:
    items = [
        Activity(
            utc(a["attempted_at"]),
            f"Scored {a['score_pct']:.0f}% on a {a['difficulty']} {a['topic']} quiz",
            a["topic"],
        )
        for a in attempts[-3:]
    ]
    items += [
        Activity(
            utc(s["started"]),
            f"Averaged {s['avg_overall']:.1f}/5 in a {s['interview_type']} interview",
        )
        for s in sessions[-2:]
    ]
    if latest_plan:
        items.append(
            Activity(utc(latest_plan["created_at"]), f"Planned week {latest_plan['week_no']}")
        )
    return sorted(items, key=lambda i: i.at, reverse=True)[:4]


def home(
    student_id: str, profile: StudentProfile | None = None, now: datetime | None = None
) -> HomeOverview:
    """Everything the Home page shows, read in five queries."""
    profile = profile or _require_profile(student_id)
    try:
        latest = db.latest_plan(student_id)
        attempts = db.quiz_history(student_id)
        sessions = db.interview_history(student_id)
        scores = db.topic_performance(student_id)
    except sqlite3.Error as e:
        raise ServiceError(
            "Your progress could not be read. Reload the page, and restart the app if it "
            "keeps failing."
        ) from e
    weakness = checks.topic_weakness(scores, agents.missing_topics(profile))
    action = decide_next_action(
        profile, latest, weakness, attempts, len(sessions), now or datetime.now(UTC)
    )
    return HomeOverview(
        profile=profile,
        weakness=weakness,
        next_action=action,
        checklist=_checklist(profile, latest, len(attempts), len(sessions)),
        recent=_recent(latest, attempts, sessions),
    )


def next_action(student_id: str | None) -> NextAction:
    """Today's focus for this student; see decide_next_action."""
    profile = current_profile(student_id)
    if profile is None:
        return decide_next_action(None, None, {}, [], 0, datetime.now(UTC))
    return home(student_id, profile).next_action
