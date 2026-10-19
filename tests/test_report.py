import json

import pytest

from evaluation import report, run_eval
from tests import factories as f


def test_report_writes_markdown_and_svg(tmp_path):
    (tmp_path / "summary.json").write_text(json.dumps(f.eval_summary()), encoding="utf-8")
    md, svg = report.main(["--results", str(tmp_path)])
    assert md.read_text(encoding="utf-8").startswith("# Evaluation results")
    assert svg.read_text(encoding="utf-8").startswith("<svg")


def test_report_requires_a_summary(tmp_path):
    with pytest.raises(SystemExit, match="run python -m evaluation.run_eval first"):
        report.main(["--results", str(tmp_path)])


def test_report_from_a_real_mock_run(tmp_path):
    args = ["--limit", "1", "--consecutive", "2", "--interviews", "--allow-mock"]
    run_eval.main([*args, "--results", str(tmp_path)])
    md, _ = report.main(["--results", str(tmp_path)])
    text = md.read_text(encoding="utf-8")
    assert "Duplicate rate over 2 quizzes" in text and "not meaningful" in text
