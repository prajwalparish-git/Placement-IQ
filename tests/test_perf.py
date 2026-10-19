"""Pure helpers of the performance tool; the full measurement is never run in tests."""

import pytest

from piq import db
from scripts import perf


@pytest.mark.parametrize(
    ("values", "q", "expected"),
    [([5, 1, 3], 50, 3), ([1, 2, 3, 4, 5, 6, 7], 90, 7), ([10], 90, 10), ([4, 8], 50, 4)],
)
def test_percentile_is_nearest_rank(values, q, expected):
    assert perf.percentile(values, q) == expected


def test_dir_size(tmp_path):
    static = tmp_path / "static"  # tmp_path itself also holds the test database
    assert perf.dir_size(static) == 0
    (static / "fonts").mkdir(parents=True)
    (static / "fonts" / "a.woff2").write_bytes(b"x" * 300)
    (static / "logo.svg").write_bytes(b"y" * 20)
    assert perf.dir_size(static) == 320


def test_query_counter_counts_calls_and_statements_and_restores_tx():
    real = db.tx
    with perf.counting_queries(db) as counts:
        db.list_students()
        db.latest_profile("missing")
    assert counts == {"calls": 2, "statements": 2}
    assert db.tx is real
    db.list_students()
    assert counts == {"calls": 2, "statements": 2}  # no counting after the block


def test_markdown_table():
    rows = [{"page": "Quiz", "median": 101.4, "p90": 130.6, "calls": 3, "statements": 4}]
    table = perf.markdown_table(rows, cold_ms=2345.2, static_bytes=2048, runs=7)
    assert "| Quiz | 101 | 131 | 3 | 4 |" in table
    assert "Cold start (fresh process to first full render): 2345 ms" in table
    assert "static/ total: 2.0 KB" in table
