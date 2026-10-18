from piq import db
from scripts import seed


def _demo_id() -> str:
    return next(s["id"] for s in db.list_students() if s["usn"] == seed.USN)


def test_seed_builds_four_weeks_of_history():
    seed.main()
    sid = _demo_id()
    assert [p.week_no for p in db.list_plans(sid)] == [1, 2, 3, 4]
    assert len(db.quiz_history(sid)) == 24
    assert len(db.past_turns(sid)) == sum(len(t) for *_, t in seed.INTERVIEWS)
    perf = db.topic_performance(sid)
    assert perf["OS"] < perf["OOP"]


def test_seeded_plans_follow_the_scores():
    seed.main()
    w1, w2, *_ = db.list_plans(_demo_id())
    # Week-1 OS score was 30%, so week 2 gives OS more time and drops strong DSA.
    assert w2.minutes_by_topic()["OS"] > w1.minutes_by_topic()["OS"]
    assert "DSA" in w1.minutes_by_topic() and "DSA" not in w2.minutes_by_topic()


def test_seed_is_idempotent():
    seed.main()
    seed.main()
    assert [s["usn"] for s in db.list_students()] == [seed.USN]
    assert len(db.quiz_history(_demo_id())) == 24
