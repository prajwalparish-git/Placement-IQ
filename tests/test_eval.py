import csv
import json

import pytest

from evaluation import run_eval


def test_refuses_mock_mode_without_flag(tmp_path):
    with pytest.raises(SystemExit, match="meaningless"):
        run_eval.main(["--results", str(tmp_path)])


def test_mock_smoke_run_writes_all_outputs(tmp_path):
    summary = run_eval.main(["--limit", "2", "--allow-mock", "--results", str(tmp_path)])
    assert summary["mode"] == "mock" and summary["errors"] == 0
    assert summary["baseline"]["cases"] == summary["placementiq"]["cases"] == 2
    assert summary["placementiq"]["plan_valid_rate"] == 1.0
    on_disk = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert on_disk["placementiq"] == summary["placementiq"]
    with open(tmp_path / "questions.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 2 * 2 * 5  # cases x systems x questions
    assert {r["system"] for r in rows} == {"baseline", "placementiq"}


def test_each_run_starts_with_a_fresh_eval_db(tmp_path):
    run_eval.main(["--limit", "1", "--allow-mock", "--results", str(tmp_path)])
    second = run_eval.main(["--limit", "1", "--allow-mock", "--results", str(tmp_path)])
    calls = {s["agent_name"]: s["calls"] for s in second["agent_stats"]}
    assert calls["baseline"] == 1  # not accumulated across runs


def test_csv_writer_handles_error_rows_first(tmp_path):
    rows = [{"case": "c1", "system": "error", "reasons": "x"}, {"case": "c2", "plan_valid": True}]
    run_eval._write_csv(tmp_path / "out.csv", rows)
    with open(tmp_path / "out.csv", encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    assert header == ["case", "system", "reasons", "plan_valid"]


def test_rate_limit_stops_the_run_but_keeps_partial_results(tmp_path, monkeypatch):
    from piq import llm

    real, calls = run_eval._baseline, []

    def limited_after_first(case):
        calls.append(case["id"])
        if len(calls) > 1:
            raise llm.RateLimited(30)
        return real(case)

    monkeypatch.setattr(run_eval, "_baseline", limited_after_first)
    summary = run_eval.main(["--limit", "3", "--allow-mock", "--results", str(tmp_path)])
    assert calls == ["c01", "c02"]  # c03 never attempted
    assert summary["stopped_early"].startswith("c02: Groq free-tier rate limit")
    assert summary["placementiq"]["cases"] == 1 and summary["errors"] == 0
    assert (tmp_path / "cases.csv").exists()


def test_resume_continues_after_a_rate_limit_without_redoing_cases(tmp_path, monkeypatch):
    from piq import llm

    real, calls = run_eval._baseline, []

    def limited_on_c02_first_time(case):
        calls.append(case["id"])
        if case["id"] == "c02" and calls.count("c02") == 1:
            raise llm.RateLimited(60)
        return real(case)

    monkeypatch.setattr(run_eval, "_baseline", limited_on_c02_first_time)
    first = run_eval.main(["--limit", "3", "--allow-mock", "--results", str(tmp_path)])
    assert first["stopped_early"].startswith("c02") and first["placementiq"]["cases"] == 1
    second = run_eval.main(["--limit", "3", "--allow-mock", "--resume", "--results", str(tmp_path)])
    assert calls == ["c01", "c02", "c02", "c03"]  # c01 was not redone
    assert second["stopped_early"] is None
    assert second["baseline"]["cases"] == second["placementiq"]["cases"] == 3
    assert {s["agent_name"] for s in second["agent_stats"]} >= {"baseline", "planner"}


def test_resume_refuses_to_mix_mock_and_live(tmp_path):
    (tmp_path / "state.json").write_text(json.dumps(run_eval._fresh_state() | {"mode": "live"}))
    with pytest.raises(SystemExit, match="saved run is live"):
        run_eval.main(["--allow-mock", "--resume", "--results", str(tmp_path)])


def test_consecutive_quizzes_measure_memory(tmp_path):
    summary = run_eval.main(
        ["--limit", "1", "--consecutive", "3", "--allow-mock", "--results", str(tmp_path)]
    )
    c = summary["consecutive"]
    assert c["topics"] == ["OS"] and c["quizzes_per_topic"] == 3
    # Mock baseline has no memory: quizzes 2 and 3 repeat quiz 1 (10 of 15 questions).
    assert c["baseline_duplicate_rate"] == 0.667
    assert c["placementiq_duplicate_rate"] == 0.0


def test_interview_probe_measures_follow_up_relevance(tmp_path):
    summary = run_eval.main(
        ["--limit", "2", "--interviews", "--allow-mock", "--results", str(tmp_path)]
    )
    assert summary["interviews"] == {
        "cases": 2,
        "followup_relevance": 1.0,
        "flagged_followup_rate": 1.0,
    }
    with open(tmp_path / "interviews.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows[0]["next_question"].startswith("You said 'I mostly worked")


def test_progress_is_saved_even_when_a_case_crashes(tmp_path, monkeypatch):
    real = run_eval._core

    def crash_on_c02(case, profile, state):
        if case["id"] == "c02":
            raise RuntimeError("unexpected bug")
        real(case, profile, state)

    monkeypatch.setattr(run_eval, "_core", crash_on_c02)
    with pytest.raises(RuntimeError):
        run_eval.main(["--limit", "3", "--allow-mock", "--results", str(tmp_path)])
    saved = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert {r["case"] for r in saved["rows"]} == {"c01"}


def test_consecutive_quizzes_resume_per_topic(tmp_path, monkeypatch):
    from piq import llm

    real, topics_run = run_eval._duplicates, []

    def limited_on_second_topic(quizzes):
        topic = quizzes[0].topic
        if topic not in topics_run:
            topics_run.append(topic)
        if (
            len(topics_run) == 2
            and topics_run.count(topic) == 1
            and not limited_on_second_topic.hit
        ):
            limited_on_second_topic.hit = True
            raise llm.RateLimited(5)
        return real(quizzes)

    limited_on_second_topic.hit = False
    monkeypatch.setattr(run_eval, "_duplicates", limited_on_second_topic)
    args = ["--limit", "3", "--consecutive", "2", "--allow-mock", "--results", str(tmp_path)]
    first = run_eval.main(args)  # cases c01-c03 cover OS, DBMS and DSA
    assert first["stopped_early"].startswith("consecutive quizzes")
    saved = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert list(saved["consecutive"]["topics"]) == ["DBMS"]  # first topic checkpointed
    second = run_eval.main([*args, "--resume"])
    assert second["consecutive"]["topics"] == ["DBMS", "DSA", "OS"]
    assert second["stopped_early"] is None


def test_consecutive_quizzes_resume_mid_topic_without_redoing_quizzes(tmp_path, monkeypatch):
    from piq import llm

    real, calls = run_eval._baseline_quiz, []

    def limited_on_third_quiz(topic):
        calls.append(topic)
        if len(calls) == 3:
            raise llm.RateLimited(5)
        return real(topic)

    monkeypatch.setattr(run_eval, "_baseline_quiz", limited_on_third_quiz)
    args = ["--limit", "1", "--consecutive", "3", "--allow-mock", "--results", str(tmp_path)]
    first = run_eval.main(args)
    assert first["stopped_early"].startswith("consecutive quizzes")
    saved = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert len(saved["consecutive"]["partial"]["OS"]["baseline"]) == 2  # both kept
    second = run_eval.main([*args, "--resume"])
    assert calls == ["OS"] * 4  # quiz 3 again after the limit; quizzes 1 and 2 not redone
    c = second["consecutive"]
    assert c["topics"] == ["OS"] and second["stopped_early"] is None
    assert c["baseline_duplicate_rate"] == 0.667  # as in an unbroken run
    assert c["placementiq_duplicate_rate"] == 0.0  # memory rebuilt from the saved quizzes
    saved = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert saved["consecutive"]["partial"] == {}


def test_every_case_is_checkpointed(tmp_path, monkeypatch):
    saves: list[int] = []
    real = run_eval._save
    monkeypatch.setattr(
        run_eval,
        "_save",
        lambda results, state: saves.append(len(state["rows"])) or real(results, state),
    )
    run_eval.main(["--limit", "3", "--allow-mock", "--results", str(tmp_path)])
    assert saves[:3] == [2, 4, 6]  # after each case, before the final save
