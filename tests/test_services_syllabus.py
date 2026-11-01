"""Integration tests for the syllabus-aware flows: domain topics on every page, quizzes over
several topics and difficulties, resume versions with the domain lock, resume advice and the
Project space. Services -> agents -> graph -> llm(mock) -> db, offline."""

from datetime import date, timedelta
from zoneinfo import ZoneInfo

import pytest

from piq import db, resume_builder, services
from piq.config import QUIZ_BATCH, RESUME_REVIEW_DAYS, TIMEZONE
from piq.services import ServiceError
from tests import factories as f

EMBEDDED = "Embedded Systems & Firmware Engineer"
ECE_RESUME = (
    "Asha Rao\nB.E in Electronics & Communication\n"
    "Skills: Embedded C, Microcontrollers, I2C, Git\n"
    "Project: Data logger on an STM32 with I2C sensors"
)


@pytest.fixture
def ece() -> str:
    sid, _ = services.onboard("ECE001", EMBEDDED, ECE_RESUME)
    return sid


@pytest.fixture
def cs() -> str:
    sid, _ = services.onboard(
        "CS0001", "Java Backend Developer", services.load_sample("java_backend_fresher.txt")
    )
    return sid


def _resume(role: str = EMBEDDED, name: str = "Asha Rao", **form) -> dict:
    res = resume_builder.build_ats_resume_data(
        full_name=name,
        email=form.pop("email", "asha@example.com"),
        phone="",
        location="",
        linkedin_url="",
        role_name=role,
        selected_skills=form.pop("skills", ["Embedded C", "I2C"]),
        experience_level="Fresher / Entry Level",
        degree="B.E in Electronics & Communication",
        institution="A college",
        grad_year="2026",
        gpa="",
        custom_project_title="Data logger",
        custom_project_tech="STM32, C",
        custom_project_desc="Built a logger\nCut data loss by 30%",
        **form,
    )
    return res


# --- the reported bug: pages showed computer-science topics to an ECE student -----------


def test_an_ece_students_pages_show_only_their_domains_topics(ece):
    cs_only = {"DBMS", "OS", "CN", "DSA", "OOP"}
    home = services.home(ece)
    assert not set(home.weakness) & cs_only
    assert "Embedded C" in home.weakness
    assert not set(services.plan_overview(ece).weakness) & cs_only
    setup = services.quiz_setup(ece)
    assert not set(setup.topics) & cs_only
    assert setup.others == ["Analog Electronics", "VLSI & Verilog", "Signals & Systems"]
    plan = services.generate_next_plan(ece)
    assert {d.topic for d in plan.days} <= set(home.weakness)  # the planner stays inside


def test_a_quiz_on_another_domains_topic_leaves_the_syllabus_unchanged(ece):
    db.save_quiz_attempt(ece, f.quiz("DBMS", n=5), [0] * 5)  # e.g. from an earlier CS role
    assert "DBMS" not in services.home(ece).weakness
    assert "DBMS" not in {m.topic for m in services.dashboard(ece).mastery}


def test_a_chosen_domain_topic_is_tracked_from_its_first_quiz(ece):
    spec = services.quiz_spec({"VLSI & Verilog": 3}, {"medium": 100}, ["VLSI & Verilog"])
    run = services.start_quiz_run(ece, spec)
    services.submit_quiz_run(ece, run, [q.correct_index for _, q in run.questions])
    assert "VLSI & Verilog" in services.quiz_setup(ece).weakness
    syl = services.dashboard(ece).syllabus
    assert "VLSI & Verilog" in syl.tracked and "VLSI & Verilog" not in syl.focus


# --- quizzes over several topics and difficulties ---------------------------------------


@pytest.mark.parametrize(("low", "high"), [(0, 0), (20, 80), (35, 35), (100, 100), (80, 20)])
def test_the_mix_slider_always_adds_up_to_100(low, high):
    mix = services.mix_from_handles(low, high)
    assert sum(mix.values()) == 100 and min(mix.values()) >= 0


@pytest.mark.parametrize("n", [1, 5, 7, 50])
def test_split_by_mix_hands_out_every_question(n):
    counts = services.split_by_mix(n, {"easy": 20, "medium": 60, "hard": 20})
    assert sum(counts.values()) == n
    assert counts["medium"] >= counts["easy"]


def test_split_by_mix_follows_the_percentages():
    assert services.split_by_mix(10, {"easy": 30, "medium": 50, "hard": 20}) == {
        "easy": 3,
        "medium": 5,
        "hard": 2,
    }
    assert services.split_by_mix(5, {"easy": 0, "medium": 100, "hard": 0})["medium"] == 5


@pytest.mark.parametrize(
    ("counts", "mix", "message"),
    [
        ({}, {"medium": 100}, "at least one topic"),
        ({"OS": 51}, {"medium": 100}, "1 to 50"),
        ({"OS": 0}, {"medium": 100}, "1 to 50"),
        ({"OS": 50, "DBMS": 50, "CN": 1}, {"medium": 100}, "at most 100"),
        ({"Thermodynamics": 5}, {"medium": 100}, "Not in your syllabus"),
        ({"OS": 5}, {"easy": 50, "medium": 40}, "add up to 100"),
        ({"OS": 5}, {"medium": 100, "insane": 0}, "only easy, medium and hard"),
    ],
)
def test_quiz_spec_rejects_bad_setups(counts, mix, message):
    with pytest.raises(ServiceError, match=message):
        services.quiz_spec(counts, mix, ["OS", "DBMS", "CN"])


def test_a_quiz_spec_lists_parts_topic_by_topic_easy_to_hard():
    spec = services.quiz_spec(
        {"OS": 10, "DBMS": 5}, {"easy": 20, "medium": 60, "hard": 20}, ["OS", "DBMS"]
    )
    assert spec.total == 15
    assert spec.parts() == [
        ("OS", "easy", 2),
        ("OS", "medium", 6),
        ("OS", "hard", 2),
        ("DBMS", "easy", 1),
        ("DBMS", "medium", 3),
        ("DBMS", "hard", 1),
    ]
    assert spec.batches == 6


def test_a_large_part_is_generated_in_critic_checked_batches_without_repeats(cs):
    events: list[str] = []
    n = 2 * QUIZ_BATCH + 3
    spec = services.quiz_spec({"OS": n}, {"medium": 100}, ["OS"])
    run = services.start_quiz_run(cs, spec, events.append)
    [part] = run.parts
    assert (part.topic, part.difficulty, len(part.questions)) == ("OS", "medium", n)
    assert len({q.text for q in part.questions}) == n  # no repeats across batches
    batches = [e for e in events if e.startswith("Batch ")]
    assert batches == [
        "Batch 1 of 3: 10 medium OS questions",
        "Batch 2 of 3: 10 medium OS questions",
        "Batch 3 of 3: 3 medium OS questions",
    ]
    assert sum(e.startswith("critic approved") for e in events) == 3


def test_submitting_a_run_saves_each_part_and_breaks_the_result_down(cs):
    spec = services.quiz_spec(
        {"OS": 4, "DBMS": 2}, {"easy": 50, "medium": 0, "hard": 50}, ["OS", "DBMS"]
    )
    run = services.start_quiz_run(cs, spec)
    assert [(p.topic, p.difficulty) for p in run.parts] == [
        ("OS", "easy"),
        ("OS", "hard"),
        ("DBMS", "easy"),
        ("DBMS", "hard"),
    ]
    right = [q.correct_index for _, q in run.questions]
    chosen = [right[0], (right[1] + 1) % 4, None, right[3], right[4], right[5]]
    result = services.submit_quiz_run(cs, run, chosen)
    assert (result.correct, result.wrong, result.skipped, result.score_pct) == (4, 1, 1, 66.7)
    by_topic = {o.label: (o.correct, o.wrong, o.skipped) for o in result.breakdown("topic")}
    assert by_topic == {"OS": (2, 1, 1), "DBMS": (2, 0, 0)}
    assert [o.label for o in result.breakdown("difficulty")] == ["easy", "hard"]
    assert [o.label for o in result.breakdown("bloom")] == ["understand"]  # the mock's level
    assert result.grid()[("OS", "easy")].correct == 1
    assert [m.n for m in result.mistakes()] == [2, 3]
    # Each topic's next difficulty comes from its hardest part, the one saved last: OS hard
    # scored 50%, which is not below 50%, so it stays hard.
    assert result.next_difficulty == {"OS": "hard", "DBMS": "hard"}
    assert services.quiz_setup(cs).last["DBMS"] == (100.0, "hard")
    [saved] = db.quiz_runs(cs)
    assert (saved["total"], saved["correct"], set(saved["topics"].split(","))) == (
        6,
        4,
        {"OS", "DBMS"},
    )
    home = services.home(cs)
    assert home.recent[0].text == "Scored 67% on a 6-question quiz: OS, DBMS"
    assert services.dashboard(cs).quizzes_taken == 1


def test_submit_rejects_answers_that_do_not_fit_the_run(cs):
    run = services.QuizRun(parts=[f.quiz(n=2)])
    with pytest.raises(ServiceError, match="do not match"):
        services.submit_quiz_run(cs, run, [0])
    with pytest.raises(ServiceError, match="Invalid answer"):
        services.submit_quiz_run(cs, run, [0, 7])


def test_recent_averages_weigh_quizzes_by_their_size(cs):
    db.save_quiz_attempt(cs, f.quiz("OS", n=10), f.answers(f.quiz("OS", n=10), 10))
    db.save_quiz_attempt(cs, f.quiz("OS", n=2, prefix="b"), f.answers(f.quiz("OS", n=2), 0))
    assert db.topic_performance(cs)["OS"] == round(100 * 10 / 12, 1)
    [os_card] = [m for m in services.dashboard(cs).mastery if m.topic == "OS"]
    assert os_card.weakness == round(1 - 10 / 12, 2)


# --- resume versions and the domain lock ----------------------------------------------


def test_saving_a_resume_versions_the_same_student_and_locks_the_domain(ece):
    assert services.locked_domain(ece) is None
    sid, n = services.save_resume(ece, "ece", _resume())
    assert (sid, n) == (ece, 1)  # the same student, not a new one each time
    assert len(services.list_students()) == 1
    assert services.locked_domain(ece).domain.id == "ece"
    sid, n = services.save_resume(ece, "ece", _resume("VLSI & Chip Design Engineer"))
    assert (sid, n) == (ece, 2)  # another role in the same domain is fine
    assert services.current_profile(ece).target_role == "VLSI & Chip Design Engineer"
    with pytest.raises(ServiceError, match="locked to Electronics & Communication"):
        services.save_resume(ece, "cs", _resume("Software Engineer"))
    with pytest.raises(ServiceError, match="locked to Electronics & Communication"):
        services.onboard("ECE001", "Software Engineer", ECE_RESUME)
    history = services.resume_history(ece)
    assert [(v.n, v.target_role) for v in history] == [
        (1, EMBEDDED),
        (2, "VLSI & Chip Design Engineer"),
    ]


def test_saving_without_a_student_creates_one_from_the_resume():
    sid, n = services.save_resume(None, "ece", _resume())
    assert n == 1 and services.current_profile(sid).name == "Asha Rao"
    assert services.locked_domain(sid).domain.id == "ece"


@pytest.mark.parametrize(
    ("domain", "res", "message"),
    [
        ("ece", _resume(email="not-an-email"), "valid email"),
        ("ece", _resume(name=""), "full name"),
        ("cs", _resume(), "not a role in this domain"),
    ],
)
def test_save_resume_validates_before_profiling(domain, res, message):
    with pytest.raises(ServiceError, match=message):
        services.save_resume(None, domain, res)
    assert services.list_students() == []


def test_resume_advice_suggests_skills_the_quizzes_now_back(ece):
    services.save_resume(ece, "ece", _resume(skills=["Embedded C"]))
    for prefix in ("a", "b"):
        quiz = f.quiz("Communication Protocols", n=5, prefix=prefix)
        db.save_quiz_attempt(ece, quiz, f.answers(quiz, 4))  # 80%: mastered after two quizzes
    services.save_project(ece, name="CAN logger", status="Done", summary="Logged CAN frames")
    advice = services.resume_advice(ece)
    [mastered] = advice.mastered
    assert (mastered.topic, mastered.pct, mastered.quizzes) == ("Communication Protocols", 80.0, 2)
    assert mastered.skills == ["I2C", "SPI", "UART"]
    assert advice.projects_to_add == ["CAN logger"]
    assert "RTOS" in advice.missing_keywords
    assert advice.quizzes_since == 2
    due = advice.review_on
    assert due == advice.last_saved.astimezone(ZoneInfo(TIMEZONE)).date() + timedelta(
        days=RESUME_REVIEW_DAYS
    )
    assert advice.due(due) and not advice.due(due - timedelta(days=1))


def test_resume_advice_before_any_version_has_no_review_date(ece):
    advice = services.resume_advice(ece)
    assert advice.review_on is None and advice.missing_keywords == []
    assert not advice.due(date.today())


# --- project space ---------------------------------------------------------------


def test_project_space_is_for_computing_domains_only(ece, cs):
    assert services.has_project_space(services.current_profile(ece))
    assert services.has_project_space(services.current_profile(cs))
    mech, _ = services.onboard("MECH01", "CAD/CAM & Product Design Engineer", "Ravi\nCAD")
    assert not services.has_project_space(services.current_profile(mech))


def test_projects_are_saved_logged_and_fed_to_the_resume(cs):
    pid = services.save_project(
        cs,
        name="Chat server",
        tech="Java,  Sockets ,",
        repo_url="https://github.com/someone/chat",
        summary="Multi-room chat over sockets\n- Handled 200 clients",
        status="Done",
    )
    services.log_project_update(cs, pid, "Added rooms")
    space = services.project_space(cs)
    [row] = space.projects
    assert (row["tech"], row["updates"]) == ("Java, Sockets", 1)
    assert sum(space.activity.values()) == 1
    assert services.resume_projects(cs) == [
        {
            "title": "Chat server",
            "tech": "Java, Sockets",
            "bullets": ["Multi-room chat over sockets", "Handled 200 clients"],
        }
    ]
    services.save_project(cs, name="Chat server", on_resume=False, project_id=pid)
    assert services.resume_projects(cs) == []
    services.delete_project(cs, pid)
    assert services.project_space(cs).projects == [] and db.project_updates(cs) == []


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"name": ""}, "name of up to 80"),
        ({"name": "x", "repo_url": "javascript:alert(1)"}, "web address"),
        ({"name": "x", "repo_url": "https://github.com/a/b) [x](y"}, "web address"),
        ({"name": "x", "status": "Abandoned"}, "Unknown status"),
        ({"name": "x", "readme": "r" * 8001}, "README"),
    ],
)
def test_project_inputs_are_validated(cs, fields, message):
    with pytest.raises(ServiceError, match=message):
        services.save_project(cs, **fields)


def test_project_names_are_unique_per_student_and_owned(cs, ece):
    pid = services.save_project(cs, name="Same")
    with pytest.raises(ServiceError, match="already have a project"):
        services.save_project(cs, name="Same")
    services.save_project(ece, name="Same")  # another student's is fine
    with pytest.raises(ServiceError, match="no longer exists"):
        services.log_project_update(ece, pid, "not mine")
    services.delete_project(ece, pid)  # not theirs: nothing happens
    assert [p["name"] for p in services.project_space(cs).projects] == ["Same"]
