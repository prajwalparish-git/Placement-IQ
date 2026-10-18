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
