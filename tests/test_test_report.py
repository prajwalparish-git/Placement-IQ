from scripts import test_report

JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="4">
  <testcase classname="tests.test_ui" name="test_dashboard_renders" time="1.5"/>
  <testcase classname="tests.test_checks" name="test_text_hash_ignores_case" time="0.01"/>
  <testcase classname="tests.test_checks" name="test_bad_input_is_rejected[png]" time="0.01">
    <failure message="boom">trace</failure>
  </testcase>
  <testcase classname="tests.test_eval" name="test_slow_path" time="0.2">
    <skipped message="later"/>
  </testcase>
</testsuite></testsuites>
"""


def test_table_is_built_from_junit_results():
    md = test_report.build_markdown(JUNIT, "2026-10-19 10:00 UTC")
    assert "**4 tests: 2 passed, 1 failed, 1 skipped**" in md
    # unit tests first, then integration, then UI, numbered in that order
    assert "| TC-001 | Unit | Deterministic critic rules | Text hash ignores case | Pass |" in md
    assert (
        "| TC-002 | Unit | Deterministic critic rules | Bad input is rejected [png] | Fail |" in md
    )
    assert "| TC-003 | Integration | Evaluation harness | Slow path | Skip |" in md
    assert "| TC-004 | System (UI) | Streamlit pages, headless | Dashboard renders | Pass |" in md
    assert "| Unit | Deterministic critic rules | `test_checks` | 2 | 1 |" in md


def test_every_test_module_has_a_layer():
    from piq.config import ROOT

    modules = {p.stem for p in (ROOT / "tests").glob("test_*.py")}
    assert modules <= set(test_report.LAYERS)
