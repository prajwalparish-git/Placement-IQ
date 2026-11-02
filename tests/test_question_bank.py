"""The local question bank: its topic map, loading and filtering, drawing, and its use in
quizzes. Tests never read the real bank: they use conftest's small `bank`."""

from piq import checks, question_bank, services, syllabus
from piq.config import QUIZ_BANK_SHARE


def test_every_mapped_topic_is_a_syllabus_topic():
    topics = {t for t in question_bank.topic_map().values() if t}
    assert topics <= syllabus.all_topics()


def test_no_bank_file_means_an_empty_bank():
    assert question_bank.size() == 0  # conftest points the bank at a missing file
    assert question_bank.draw("DBMS", "easy", 5, [], "s") == []


def test_only_valid_distinct_mapped_questions_load(bank):
    assert question_bank.available("DBMS", "easy") == 6
    assert question_bank.available("DBMS", "medium") == 4
    assert question_bank.size() == 10


def test_draw_is_reproducible_avoids_seen_text_and_maps_the_answer(bank):
    a = question_bank.draw("DBMS", "easy", 3, [], "seed")
    assert [q.text for q in a] == [
        q.text for q in question_bank.draw("DBMS", "easy", 3, [], "seed")
    ]
    seen = [q.text.upper() + "  " for q in a]  # compared like the critic's duplicate check
    rest = question_bank.draw("DBMS", "easy", 10, seen, "seed")
    assert len(rest) == 3 and not {checks.text_hash(q.text) for q in rest} & {
        checks.text_hash(t) for t in seen
    }
    assert all(q.correct_index == 2 and q.options[2] == "third" for q in a)
    assert question_bank.draw("DBMS", "easy", 0, [], "seed") == []


def test_a_quiz_part_takes_a_share_from_the_bank_after_the_generated_questions(bank):
    sid, _ = services.onboard(
        "CS0001", "Java Backend Developer", services.load_sample("java_backend_fresher.txt")
    )
    events = []
    spec = services.quiz_spec({"DBMS": 4}, {"easy": 100, "medium": 0, "hard": 0}, ["DBMS"])
    run = services.start_quiz_run(sid, spec, events.append)
    [part] = run.parts
    assert services.bank_share(4) == int(4 * QUIZ_BANK_SHARE) == 2
    assert len(part.questions) == 4
    generated, banked = part.questions[:2], part.questions[2:]
    assert all(q.text.startswith("[mock]") for q in generated)
    assert all(q.text.startswith("Bank question") for q in banked)
    assert any("from the question bank" in e for e in events)
    # Answered questions are not drawn again: the next quiz takes the other bank questions.
    services.submit_quiz_run(sid, run, [q.correct_index for _, q in run.questions])
    again = services.start_quiz_run(sid, spec)
    assert not {q.text for q in again.parts[0].questions} & {q.text for q in banked}


def test_a_one_question_part_is_always_generated(bank):
    sid, _ = services.onboard(
        "CS0001", "Java Backend Developer", services.load_sample("java_backend_fresher.txt")
    )
    spec = services.quiz_spec({"DBMS": 1}, {"easy": 100, "medium": 0, "hard": 0}, ["DBMS"])
    [part] = services.start_quiz_run(sid, spec).parts
    assert part.questions[0].text.startswith("[mock]")
