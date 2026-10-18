"""Minimal LangGraph: generate -> verify -> (retry | done).

One graph shape is shared by every agent; each `Task` supplies its own
generate/verify functions. Persistence stays with the caller.

    START -> generate -> verify --approved / out of retries--> END
                ^           |
                +--retry----+
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cache
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from piq import db
from piq.config import settings

# generate(inputs, feedback) -> (output, agent_logs id); verify(inputs, output) -> reasons
Generate = Callable[[dict, list[str]], tuple[BaseModel, int]]
Verify = Callable[[dict, BaseModel], list[str]]
OnEvent = Callable[[str], None]


class CriticState(TypedDict):
    inputs: dict
    output: Any
    log_id: int
    reasons: list[str]
    attempt: int


@dataclass(frozen=True)
class Task:
    name: str
    generate: Generate
    verify: Verify


@dataclass
class RunResult:
    output: Any
    approved: bool
    attempts: int
    reasons: list[str] = field(default_factory=list)


class CriticRejected(RuntimeError):
    def __init__(self, task: str, reasons: list[str]):
        self.reasons = reasons
        super().__init__(f"{task}: rejected after retries: {'; '.join(reasons)}")


def build(task: Task):
    def generate(s: CriticState) -> dict:
        out, log_id = task.generate(s["inputs"], s["reasons"])
        return {"output": out, "log_id": log_id, "attempt": s["attempt"] + 1}

    def verify(s: CriticState) -> dict:
        reasons = task.verify(s["inputs"], s["output"])
        db.mark_log(s["log_id"], not reasons, s["attempt"] - 1, "; ".join(reasons) or None)
        return {"reasons": reasons}

    def route(s: CriticState) -> str:
        if not s["reasons"] or s["attempt"] > settings().max_critic_retries:
            return "done"
        return "retry"

    g = StateGraph(CriticState)
    g.add_node("generate", generate)
    g.add_node("verify", verify)
    g.add_edge(START, "generate")
    g.add_edge("generate", "verify")
    g.add_conditional_edges("verify", route, {"retry": "generate", "done": END})
    return g.compile()


_compiled = cache(build)  # one compiled graph per Task object


def run(task: Task, inputs: dict, on_event: OnEvent | None = None) -> RunResult:
    """Run the loop, reporting each step through `on_event` (the UI status feed)."""
    graph = _compiled(task)
    state: dict = {"inputs": inputs, "output": None, "log_id": 0, "reasons": [], "attempt": 0}
    for update in graph.stream(state, stream_mode="updates"):
        for node, delta in update.items():
            state.update(delta)
            if on_event is None:
                continue
            if node == "generate":
                on_event(f"{task.name}: generated (attempt {state['attempt']})")
            elif delta["reasons"]:
                on_event(f"critic rejected {task.name}: {'; '.join(delta['reasons'])}")
            else:
                on_event(f"critic approved {task.name}")
    return RunResult(state["output"], not state["reasons"], state["attempt"], state["reasons"])


def run_or_raise(task: Task, inputs: dict, on_event: OnEvent | None = None) -> Any:
    r = run(task, inputs, on_event)
    if not r.approved:
        raise CriticRejected(task.name, r.reasons)
    return r.output
