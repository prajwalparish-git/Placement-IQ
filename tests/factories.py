"""Plain model builders so lower-layer tests don't depend on agents or the mock LLM."""

from piq.schemas import AnswerEvaluation, DayPlan, Question, QuizSet, StudentProfile, WeeklyPlan


def profile(
    role: str = "Java Backend Developer",
    matched: tuple[str, ...] = ("Java", "SQL"),
    missing: tuple[str, ...] = ("Operating Systems", "Data Structures"),
    **overrides,
) -> StudentProfile:
    data = {
        "name": "Test Student",
        "education": "B.E. (test)",
        "skills": list(matched),
        "projects": ["Demo project"],
        "internships": [],
        "matched_skills": list(matched),
        "resume_feedback": ["Add measurable results."],
        "target_role": role,
        "missing_skills": list(missing),
        "readiness_score": round(100 * len(matched) / (len(matched) + len(missing))),
    }
    return StudentProfile(**(data | overrides))


def question(
    text: str = "What is a page fault in an OS?",
    options: tuple[str, ...] = ("w", "x", "y", "z"),
    correct: int = 0,
    bloom: str = "remember",
) -> Question:
    return Question(
        text=text, options=list(options), correct_index=correct, explanation="e", bloom_level=bloom
    )


def quiz(topic: str = "OS", difficulty: str = "easy", n: int = 2, prefix: str = "test") -> QuizSet:
    return QuizSet(
        topic=topic,
        difficulty=difficulty,
        questions=[
            question(f"{prefix} {topic} question number {i}", correct=i % 4) for i in range(n)
        ],
    )


def answers(q: QuizSet, right: int) -> list[int]:
    """The first `right` answers are correct, the rest wrong."""
    return [
        x.correct_index if i < right else (x.correct_index + 1) % 4
        for i, x in enumerate(q.questions)
    ]


def plan(
    week: int = 1,
    topics: tuple[str, ...] = ("OS",) * 7,
    minutes: tuple[int, ...] = (60,) * 7,
) -> WeeklyPlan:
    return WeeklyPlan(
        week_no=week,
        rationale="test",
        days=[
            DayPlan(day=i + 1, topic=t, subtopics=["a", "b"], duration_min=m, practice_goal="g")
            for i, (t, m) in enumerate(zip(topics, minutes, strict=True))
        ],
    )


def evaluation(**scores: int) -> AnswerEvaluation:
    base = {"relevance": 3, "depth": 3, "structure": 3, "clarity": 3}
    return AnswerEvaluation(
        **(base | scores), strengths=["s"], improvements=["i"], model_answer="m"
    )
