import pytest

from piq import db, graph
from piq.config import settings


def _logged_task(outputs: list[str], name: str = "t") -> graph.Task:
    """generate yields `outputs` in order; verify rejects anything equal to 'bad'."""
    it = iter(outputs)

    def gen(inp, reasons, previous):
        return next(it), db.log_call(name, "mock", 0, 0, 0)

    return graph.Task(name, gen, lambda inp, out: ["is bad"] if out == "bad" else [])


def test_loop_retries_then_approves_and_reports_events():
    events: list[str] = []
    r = graph.run(_logged_task(["bad", "good"], "a"), {}, events.append)
    assert (r.output, r.approved, r.attempts, r.reasons) == ("good", True, 2, [])
    assert events == [
        "a: generated (attempt 1)",
        "critic rejected a: is bad",
        "a: generated (attempt 2)",
        "critic approved a",
    ]


def test_loop_stops_after_retry_budget():
    r = graph.run(_logged_task(["bad"] * 5, "b"), {})
    assert (r.approved, r.attempts, r.reasons) == (False, 3, ["is bad"])  # 1 + MAX_CRITIC_RETRIES
    with pytest.raises(graph.CriticRejected, match="is bad") as exc:
        graph.run_or_raise(_logged_task(["bad"] * 5, "c"), {})
    assert exc.value.reasons == ["is bad"]


def test_zero_retry_budget_means_single_attempt(monkeypatch):
    monkeypatch.setenv("MAX_CRITIC_RETRIES", "0")
    settings.cache_clear()
    r = graph.run(_logged_task(["bad", "good"], "z"), {})
    assert (r.approved, r.attempts) == (False, 1)


def test_retry_receives_previous_rejection_reasons():
    seen: list[list[str]] = []

    def gen(inp, reasons, previous):
        seen.append((list(reasons), previous))
        return ("good" if reasons else "bad"), db.log_call("r", "mock", 0, 0, 0)

    task = graph.Task("r", gen, lambda inp, out: [] if out == "good" else ["must be good"])
    assert graph.run_or_raise(task, {"x": 1}) == "good"
    assert seen == [([], None), (["must be good"], "bad")]  # retry sees the rejected output


def test_every_attempt_is_marked_in_agent_logs():
    graph.run(_logged_task(["bad", "bad", "good"], "m"), {})
    with db.tx() as c:
        rows = c.execute(
            "SELECT critic_approved, retry_count, reject_reason FROM agent_logs ORDER BY id"
        ).fetchall()
    assert [tuple(r) for r in rows] == [(0, 0, "is bad"), (0, 1, "is bad"), (1, 2, None)]


def test_a_verify_that_raises_marks_the_attempt_failed():
    def gen(inp, reasons, previous):
        return "x", db.log_call("v", "mock", 3, 4, 5)

    def verify(inp, out):
        raise RuntimeError("critic unavailable")

    with pytest.raises(RuntimeError, match="critic unavailable"):
        graph.run(graph.Task("v", gen, verify), {})
    with db.tx() as c:
        [row] = c.execute("SELECT critic_approved, retry_count, reject_reason FROM agent_logs")
    assert row["critic_approved"] is None and row["retry_count"] == 0
    assert row["reject_reason"] == "failed: verify raised RuntimeError: critic unavailable"


def test_compiled_graph_is_cached_per_task_and_exports_mermaid():
    task = _logged_task([], "x")
    assert graph._compiled(task) is graph._compiled(task)
    mermaid = graph.build(task).get_graph().draw_mermaid()
    assert "generate" in mermaid and "verify" in mermaid and "retry" in mermaid
