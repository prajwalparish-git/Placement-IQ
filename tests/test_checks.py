from piq import checks
from piq.config import TOPICS
from piq.schemas import InterviewTurn, ProfileExtraction, QuizSet
from tests import factories as f


def _extraction(**kw) -> ProfileExtraction:
    data = {
        "name": "n",
        "education": "e",
        "skills": ["Java"],
        "projects": [],
        "internships": [],
        "matched_skills": ["Java"],
        "resume_feedback": ["f"],
    }
    return ProfileExtraction(**(data | kw))


def _turn(question: str) -> InterviewTurn:
    return InterviewTurn(question=question, intent="i", is_followup=False, is_final=False)


def test_text_hash_ignores_case_whitespace_and_punctuation():
    assert checks.text_hash("What is a  Deadlock?") == checks.text_hash("what is a deadlock")
    assert checks.text_hash("What is a deadlock?") != checks.text_hash("What is a mutex?")


def test_weakness_prefers_quiz_evidence_over_resume_gaps():
    w = checks.topic_weakness({"OS": 30.0, "DSA": 90.0}, missing_topics={"OS", "DBMS"})
    assert set(w) == set(TOPICS)
    assert (w["OS"], w["DSA"], w["DBMS"], w["CN"]) == (0.7, 0.1, 0.7, 0.4)
    assert checks.weak_topics(w) == ["DBMS", "OS"]  # ties keep TOPICS order


def test_weak_topics_sorted_by_weakness_and_threshold_is_strict():
    w = {"OS": 0.6, "DBMS": 0.9, "CN": 0.5, "DSA": 0.2}
    assert checks.weak_topics(w) == ["DBMS", "OS"]  # 0.5 is not weak


def test_plan_rejected_when_weak_topics_underweighted():
    weakness = checks.topic_weakness({"OS": 20.0}, set())
    plan = f.plan(
        topics=("OS", "DSA", "DSA", "CN", "CN", "OOP", "OOP"),
        minutes=(30, 120, 120, 120, 120, 120, 120),
    )
    [reason] = checks.check_plan(plan, 1, weakness)
    assert "at least 50%" in reason


def test_plan_rejected_when_a_weak_topic_is_missing():
    weakness = checks.topic_weakness({"OS": 20.0, "CN": 10.0}, set())
    plan = f.plan(topics=("OS",) * 7, minutes=(120,) * 7)
    assert any("missing from the plan: ['CN']" in r for r in checks.check_plan(plan, 1, weakness))


def test_plan_accepted_when_weak_topics_dominate():
    weakness = checks.topic_weakness({"OS": 20.0}, set())
    plan = f.plan(
        topics=("OS", "OS", "OS", "OS", "DSA", "CN", "OOP"),
        minutes=(120, 120, 120, 120, 60, 60, 60),
    )
    assert checks.check_plan(plan, 1, weakness) == []


def test_plan_without_weak_topics_skips_share_rule():
    strong = checks.topic_weakness(dict.fromkeys(TOPICS, 90.0), set())
    assert checks.check_plan(f.plan(), 1, strong) == []


def test_plan_wrong_week_and_bad_day_numbers():
    plan = f.plan(week=3)
    plan.days[6].day = 1
    assert len(checks.check_plan(plan, 2, checks.topic_weakness({}, set()))) == 2


def test_quiz_flags_duplicates_and_non_distinct_options():
    quiz = QuizSet(
        topic="OS",
        difficulty="easy",
        questions=[
            f.question("What is a deadlock in OS?"),
            f.question("Which scheduler is preemptive?", options=("a", "A ", "b", "c")),
            f.question("what is a deadlock in os"),
        ],
    )
    reasons = checks.check_quiz(quiz, "OS", "easy", 3, previous=["Which scheduler is preemptive"])
    assert sum("duplicate" in r for r in reasons) == 2  # one vs history, one within the set
    assert any("question 1: options are not distinct" in r for r in reasons)


def test_quiz_topic_difficulty_and_count_mismatch():
    quiz = f.quiz(topic="CN", difficulty="hard", n=1)
    assert len(checks.check_quiz(quiz, "OS", "easy", 5, previous=[])) == 3


def test_clean_quiz_passes():
    assert checks.check_quiz(f.quiz(n=5), "OS", "easy", 5, previous=["unrelated question"]) == []


def test_profile_matched_skills_must_come_from_required_list():
    reasons = checks.check_profile(_extraction(matched_skills=["java", "Kubernetes"]), ["Java"])
    assert len(reasons) == 1 and "Kubernetes" in reasons[0]  # case-insensitive match for java


def test_profile_with_no_skills_is_rejected():
    assert checks.check_profile(_extraction(skills=[], matched_skills=[]), ["Java"])


def test_turn_checks_single_question_and_repeats():
    assert checks.check_turn(_turn("Why OS? Why DBMS? Why CN?"), []) == [
        "ask exactly one question per turn"
    ]
    assert checks.check_turn(_turn("Tell me about yourself."), ["tell me about yourself"])
    assert checks.check_turn(_turn("What did you build?"), ["Tell me about yourself."]) == []


def test_question_reasons_round_trip():
    reasons = [checks.question_reason(2, "two answers"), checks.question_reason(0, "dup: a: b")]
    assert checks.question_issues(reasons) == {2: ["two answers"], 0: ["dup: a: b"]}
    assert checks.question_issues([*reasons, "topic must be OS, got CN"]) is None
    assert checks.question_issues([]) is None
