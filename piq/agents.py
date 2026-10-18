"""The agents. Each generation task runs through the critic graph in piq/graph.py.

Agents read inputs and return validated models; they never write domain tables
(callers persist results). They do write agent_logs via piq.llm.
"""

import json
from functools import lru_cache

from piq import checks, llm, prompts
from piq.config import DATA_DIR, INTERVIEW_MAX_TURNS, QUIZ_SIZE
from piq.graph import OnEvent, Task, run_or_raise
from piq.schemas import (
    AnswerEvaluation,
    InterviewTurn,
    ProfileExtraction,
    QuizCritique,
    QuizSet,
    StudentProfile,
    WeeklyPlan,
)


def _feedback(reasons: list[str]) -> str:
    if not reasons:
        return ""
    bullets = "\n".join(f"- {r}" for r in reasons)
    return f"\n\nYour previous attempt was REJECTED for these reasons. Fix all of them:\n{bullets}"


@lru_cache
def roles() -> dict[str, dict[str, str | None]]:
    """role -> {required skill -> syllabus topic or null}."""
    return json.loads((DATA_DIR / "role_skills.json").read_text(encoding="utf-8"))["roles"]


def missing_topics(profile: StudentProfile) -> set[str]:
    req = roles().get(profile.target_role, {})
    return {t for s in profile.missing_skills if (t := req.get(s))}


# --- Profile Agent -------------------------------------------------------------


def _profile_gen(inp: dict, reasons: list[str]) -> tuple[ProfileExtraction, int]:
    required = list(roles()[inp["target_role"]])
    user = (
        f"Target role: {inp['target_role']}\nRequired skills: {json.dumps(required)}\n\n"
        f"Resume:\n{inp['resume_text'][:12000]}{_feedback(reasons)}"
    )
    ctx = {**inp, "required_skills": required}
    return llm.call(
        ProfileExtraction,
        agent="profile",
        system=prompts.PROFILE,
        user=user,
        context=ctx,
        size="small",
        temperature=0.1,
    )


PROFILE_TASK = Task(
    "profile",
    _profile_gen,
    lambda inp, out: checks.check_profile(out, list(roles()[inp["target_role"]])),
)


def create_profile(
    resume_text: str, target_role: str, on_event: OnEvent | None = None
) -> StudentProfile:
    ext: ProfileExtraction = run_or_raise(
        PROFILE_TASK, {"resume_text": resume_text, "target_role": target_role}, on_event
    )
    required = list(roles()[target_role])
    canon = {s.lower(): s for s in required}
    matched = sorted({canon[s.lower()] for s in ext.matched_skills})
    return StudentProfile(
        **ext.model_dump(exclude={"matched_skills"}),
        matched_skills=matched,
        target_role=target_role,
        missing_skills=[s for s in required if s not in matched],
        readiness_score=round(100 * len(matched) / len(required)),
    )


# --- Planner Agent -------------------------------------------------------------


def _planner_gen(inp: dict, reasons: list[str]) -> tuple[WeeklyPlan, int]:
    w = inp["weakness"]
    weak = set(checks.weak_topics(w))
    table = "\n".join(
        f"- {t}: weakness {v:.2f}{' WEAK' if t in weak else ''}"
        f"{f', recent quiz avg {inp["scores"][t]}%' if t in inp['scores'] else ', no quiz yet'}"
        for t, v in sorted(w.items(), key=lambda kv: -kv[1])
    )
    prev = inp["previous_minutes"]
    user = (
        f"Week number: {inp['week_no']}\nTarget role: {inp['target_role']}\n"
        f"Missing skills: {', '.join(inp['missing_skills']) or 'none'}\n\n"
        f"Topic weakness:\n{table}\n\n"
        f"Previous week minutes per topic: {json.dumps(prev) if prev else 'none (first week)'}"
        f"{_feedback(reasons)}"
    )
    return llm.call(
        WeeklyPlan,
        agent="planner",
        system=prompts.PLANNER,
        user=user,
        context=inp,
        student_id=inp["student_id"],
        temperature=0.3,
    )


PLANNER_TASK = Task(
    "planner",
    _planner_gen,
    lambda inp, out: checks.check_plan(out, inp["week_no"], inp["weakness"]),
)


def planner_inputs(
    profile: StudentProfile,
    scores: dict[str, float],
    week_no: int,
    previous: WeeklyPlan | None = None,
    student_id: str | None = None,
) -> dict:
    return {
        "student_id": student_id,
        "week_no": week_no,
        "target_role": profile.target_role,
        "missing_skills": profile.missing_skills,
        "scores": scores,
        "weakness": checks.topic_weakness(scores, missing_topics(profile)),
        "previous_minutes": previous.minutes_by_topic() if previous else None,
    }


def plan_week(
    profile: StudentProfile,
    scores: dict[str, float],
    week_no: int,
    previous: WeeklyPlan | None = None,
    student_id: str | None = None,
    on_event: OnEvent | None = None,
) -> WeeklyPlan:
    inp = planner_inputs(profile, scores, week_no, previous, student_id)
    return run_or_raise(PLANNER_TASK, inp, on_event)


# --- Quiz Agent + LLM critic ---------------------------------------------------


def suggest_difficulty(last_score: float | None, current: str = "medium") -> str:
    order = ["easy", "medium", "hard"]
    if last_score is None:
        return current
    i = order.index(current)
    if last_score >= 80:
        i = min(i + 1, 2)
    elif last_score < 50:
        i = max(i - 1, 0)
    return order[i]


def _quiz_gen(inp: dict, reasons: list[str]) -> tuple[QuizSet, int]:
    prev = "\n".join(f"- {q}" for q in inp["previous"][:15]) or "none"
    user = (
        f"Topic: {inp['topic']}\nDifficulty: {inp['difficulty']}\n"
        f"Number of questions: {inp['count']}\n\nPrevious questions (do not repeat):\n{prev}"
        f"{_feedback(reasons)}"
    )
    return llm.call(
        QuizSet,
        agent="quiz",
        system=prompts.QUIZ,
        user=user,
        context={**inp, "first_attempt": not reasons},
        student_id=inp["student_id"],
        temperature=0.8,
    )


def verify_quiz(inp: dict, quiz: QuizSet) -> list[str]:
    reasons = checks.check_quiz(
        quiz, inp["topic"], inp["difficulty"], inp["count"], inp["previous"]
    )
    if reasons:  # deterministic failures: skip the paid LLM check
        return reasons
    listing = "\n\n".join(
        f"[{i}] {q.text}\n"
        + "\n".join(f"  {j}. {o}" for j, o in enumerate(q.options))
        + f"\n  marked correct: {q.correct_index}"
        for i, q in enumerate(quiz.questions)
    )
    critique, _ = llm.call(
        QuizCritique,
        agent="critic",
        system=prompts.CRITIC,
        user=f"Topic: {quiz.topic}\n\n{listing}",
        context={"count": len(quiz.questions)},
        student_id=inp["student_id"],
        temperature=0.0,
    )
    return [
        f"question {v.index}: {v.reason or 'invalid'}" for v in critique.verdicts if not v.valid
    ]


QUIZ_TASK = Task("quiz", _quiz_gen, verify_quiz)


def quiz_inputs(
    topic: str,
    difficulty: str,
    previous: list[str],
    count: int = QUIZ_SIZE,
    student_id: str | None = None,
) -> dict:
    return {
        "topic": topic,
        "difficulty": difficulty,
        "count": count,
        "previous": previous,
        "student_id": student_id,
    }


def make_quiz(
    topic: str,
    difficulty: str,
    previous: list[str],
    count: int = QUIZ_SIZE,
    student_id: str | None = None,
    on_event: OnEvent | None = None,
) -> QuizSet:
    inp = quiz_inputs(topic, difficulty, previous, count, student_id)
    return run_or_raise(QUIZ_TASK, inp, on_event)


# --- Interview Agent + answer evaluator ----------------------------------------


def _profile_brief(p: StudentProfile) -> str:
    return (
        f"Candidate: {p.name}; target role: {p.target_role}; education: {p.education}\n"
        f"Skills: {', '.join(p.skills)}\nProjects: {'; '.join(p.projects) or 'none listed'}\n"
        f"Internships: {'; '.join(p.internships) or 'none'}"
    )


def _interview_gen(inp: dict, reasons: list[str]) -> tuple[InterviewTurn, int]:
    hist = "\n".join(f"Q: {h['question']}\nA: {h['answer']}" for h in inp["history"]) or "none"
    past = "\n".join(f"Q: {h['question']}\nA: {h['answer'][:300]}" for h in inp["past"][:5])
    user = (
        f"{inp['brief']}\n\nEarlier sessions (memory):\n{past or 'none'}\n\n"
        f"This session so far:\n{hist}\n\n"
        f"Turn {len(inp['history']) + 1} of {inp['max_turns']}.{_feedback(reasons)}"
    )
    system = prompts.INTERVIEWER.format(interview_type=inp["interview_type"])
    return llm.call(
        InterviewTurn,
        agent="interviewer",
        system=system,
        user=user,
        context=inp,
        student_id=inp["student_id"],
        temperature=0.7,
    )


INTERVIEW_TASK = Task(
    "interviewer", _interview_gen, lambda inp, out: checks.check_turn(out, inp["asked"])
)


def next_question(
    profile: StudentProfile,
    interview_type: str,
    history: list[dict],
    past: list[dict],
    student_id: str | None = None,
    on_event: OnEvent | None = None,
) -> InterviewTurn:
    inp = {
        "brief": _profile_brief(profile),
        "interview_type": interview_type,
        "history": history,
        "past": past,
        "asked": [h["question"] for h in history + past],
        "max_turns": INTERVIEW_MAX_TURNS,
        "student_id": student_id,
    }
    turn: InterviewTurn = run_or_raise(INTERVIEW_TASK, inp, on_event)
    # Turn bookkeeping is a fact, not a judgment: enforce it in code.
    return turn.model_copy(
        update={
            "is_followup": turn.is_followup and bool(history),
            "is_final": turn.is_final or len(history) + 1 >= INTERVIEW_MAX_TURNS,
        }
    )


def evaluate_answer(
    profile: StudentProfile,
    interview_type: str,
    question: str,
    answer: str,
    student_id: str | None = None,
) -> AnswerEvaluation:
    user = (
        f"{_profile_brief(profile)}\nInterview type: {interview_type}\n\n"
        f"Question: {question}\nAnswer: {answer}"
    )
    ev, _ = llm.call(
        AnswerEvaluation,
        agent="evaluator",
        system=prompts.EVALUATOR,
        user=user,
        context={"question": question, "answer": answer},
        student_id=student_id,
        temperature=0.2,
    )
    return ev
