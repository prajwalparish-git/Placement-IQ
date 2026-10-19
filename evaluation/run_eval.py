"""Baseline (one prompt) vs PlacementIQ (agents + critic) on the frozen test set.

    python -m evaluation.run_eval [--limit N] [--consecutive N] [--interviews]
                                  [--resume] [--allow-mock] [--results DIR]

Every case: plan validity, weak-topic share, quiz validity and duplicates against the
case's question history. Both systems are judged by the same deterministic checks and the
same LLM critic.
  --consecutive N  duplicate rate over N back-to-back quizzes per topic; the baseline has
                   no memory, PlacementIQ excludes everything it asked before
  --interviews     follow-up relevance: after a deliberately vague answer, does the next
                   question follow up on it? Judged by the small model
  --resume         keep finished cases from the last run and continue (quota limits)

Writes evaluation/results/: state.json (resumable), cases.csv, questions.csv (for manual
labelling), interviews.csv, summary.json and eval.db (agent_logs of this evaluation).
Quota: ~7 calls per case, +3 per case with --interviews, ~4 per consecutive quiz.
Stops early on a rate limit, keeping partial results; rerun with --resume.
"""

import argparse
import csv
import json
import os
from pathlib import Path

from piq import agents, checks, db, graph, llm, prompts
from piq.config import QUIZ_SIZE, RESULTS_DIR, settings
from piq.schemas import BaselineOutput, FollowUpJudgement, QuizSet, StudentProfile

HERE = Path(__file__).resolve().parent
VAGUE_ANSWER = "I mostly worked on the backend part of my main project using a framework."
CONSECUTIVE_DIFFICULTY = "medium"


def _fresh_state() -> dict:
    return {"mode": None, "rows": [], "questions": [], "interviews": [], "consecutive": None}


def _baseline(case: dict) -> BaselineOutput:
    user = (
        f"Target role: {case['target_role']}\nWeek number: {case['week_no']}\n"
        f"Quiz scores (%): {json.dumps(case['scores']) if case['scores'] else 'none yet'}\n"
        f"Quiz topic: {case['quiz_topic']}, difficulty {case['difficulty']}, "
        f"{QUIZ_SIZE} questions. Previous questions: {json.dumps(case['previous_questions'])}\n\n"
        f"Resume:\n{case['resume_text']}"
    )
    ctx = {
        "week_no": case["week_no"],
        "topic": case["quiz_topic"],
        "difficulty": case["difficulty"],
        "count": QUIZ_SIZE,
        "previous": case["previous_questions"],
    }
    out, _ = llm.call(
        BaselineOutput,
        agent="baseline",
        system=prompts.BASELINE,
        user=user,
        context=ctx,
        temperature=0.4,
    )
    return out


def _row(case: dict, system: str, plan, quiz, weakness, quiz_inp, attempts=(1, 1)) -> dict:
    weak = checks.weak_topics(weakness)
    minutes = plan.minutes_by_topic()
    plan_reasons = checks.check_plan(plan, case["week_no"], weakness)
    # Same judge for both systems: deterministic checks, then the LLM critic.
    quiz_reasons = agents.verify_quiz(quiz_inp, quiz)
    return {
        "case": case["id"],
        "tag": case["tag"],
        "system": system,
        "plan_valid": not plan_reasons,
        "weak_share": round(sum(minutes.get(t, 0) for t in weak) / sum(minutes.values()), 2)
        if weak
        else "",
        "quiz_valid": not quiz_reasons,
        "quiz_duplicates": sum("duplicate" in r for r in quiz_reasons),
        "plan_attempts": attempts[0],
        "quiz_attempts": attempts[1],
        "reasons": " | ".join(plan_reasons + quiz_reasons),
    }


def _core(case: dict, profile: StudentProfile, state: dict) -> None:
    """Baseline and PlacementIQ on one case: plan + quiz, judged identically.

    All-or-nothing: state is only updated once both systems are generated and judged.
    """
    weakness = checks.topic_weakness(case["scores"], agents.missing_topics(profile))
    q_inp = agents.quiz_inputs(case["quiz_topic"], case["difficulty"], case["previous_questions"])
    base = _baseline(case)
    p = graph.run(
        agents.PLANNER_TASK, agents.planner_inputs(profile, case["scores"], case["week_no"])
    )
    q = graph.run(agents.QUIZ_TASK, q_inp)
    rows = [
        _row(case, "baseline", base.plan, base.quiz, weakness, q_inp),
        _row(case, "placementiq", p.output, q.output, weakness, q_inp, (p.attempts, q.attempts)),
    ]
    questions = [
        {
            "case": case["id"],
            "system": system,
            "topic": quiz.topic,
            "text": qq.text,
            "options": " || ".join(qq.options),
            "marked": qq.correct_index,
            "label_valid (y/n)": "",
        }
        for system, quiz in (("baseline", base.quiz), ("placementiq", q.output))
        for qq in quiz.questions
    ]
    state["rows"] += rows
    state["questions"] += questions


def _interview_probe(case: dict, profile: StudentProfile) -> dict:
    """Ask, answer vaguely, ask again; a judge decides if the second question follows up."""
    first = agents.next_question(profile, "Project", [], [])
    history = [{"question": first.question, "answer": VAGUE_ANSWER}]
    second = agents.next_question(profile, "Project", history, [])
    verdict, _ = llm.call(
        FollowUpJudgement,
        agent="judge",
        system=prompts.JUDGE,
        user=(
            f"QUESTION: {first.question}\nANSWER: {VAGUE_ANSWER}\nNEXT QUESTION: {second.question}"
        ),
        context={"answer": VAGUE_ANSWER, "question": second.question},
        size="small",
        temperature=0.0,
    )
    return {
        "case": case["id"],
        "first_question": first.question,
        "next_question": second.question,
        "flagged_followup": second.is_followup,
        "references_answer": verdict.references_answer,
        "judge_reason": verdict.reason,
    }


def _duplicates(quizzes: list[QuizSet]) -> list[int]:
    """[repeated questions, total questions] across a sequence of quizzes."""
    seen: set[str] = set()
    dups = total = 0
    for quiz in quizzes:
        for q in quiz.questions:
            h = checks.text_hash(q.text)
            dups += h in seen
            seen.add(h)
            total += 1
    return [dups, total]


def _consecutive(topics: list[str], n: int, state: dict, checkpoint) -> None:
    """Fill state["consecutive"] topic by topic (checkpointed, so a resume skips done ones)."""
    out = state["consecutive"]
    if not out or out["quizzes_per_topic"] != n:
        out = state["consecutive"] = {"quizzes_per_topic": n, "topics": {}}
    for topic in topics:
        if topic in out["topics"]:
            continue
        print(f"consecutive quizzes: {topic} x{n} per system ...", flush=True)
        baseline = [
            llm.call(
                QuizSet,
                agent="baseline_quiz",
                system=prompts.QUIZ,
                user=f"Topic: {topic}\nDifficulty: {CONSECUTIVE_DIFFICULTY}\n"
                f"Number of questions: {QUIZ_SIZE}",
                context={
                    "topic": topic,
                    "difficulty": CONSECUTIVE_DIFFICULTY,
                    "count": QUIZ_SIZE,
                    "previous": [],
                },
                temperature=0.8,
            )[0]
            for _ in range(n)
        ]
        ours: list[QuizSet] = []
        for _ in range(n):
            asked = [q.text for quiz in ours for q in quiz.questions]
            inp = agents.quiz_inputs(topic, CONSECUTIVE_DIFFICULTY, asked)
            ours.append(graph.run(agents.QUIZ_TASK, inp).output)  # judged as produced
        out["topics"][topic] = {"baseline": _duplicates(baseline), "placementiq": _duplicates(ours)}
        _duplicate_rates(out)
        checkpoint()
    _duplicate_rates(out)


def _duplicate_rates(out: dict) -> None:
    for system in ("baseline", "placementiq"):
        dups = sum(t[system][0] for t in out["topics"].values())
        total = sum(t[system][1] for t in out["topics"].values())
        out[f"{system}_duplicate_rate"] = round(dups / total, 3) if total else None


def _summary(state: dict, stopped: str | None) -> dict:
    rows = state["rows"]
    summary: dict = {"mode": state["mode"], "stopped_early": stopped}
    for system in ("baseline", "placementiq"):
        rs = [r for r in rows if r["system"] == system]
        if not rs:
            continue
        shares = [r["weak_share"] for r in rs if r["weak_share"] != ""]
        summary[system] = {
            "cases": len(rs),
            "plan_valid_rate": round(sum(r["plan_valid"] for r in rs) / len(rs), 2),
            "quiz_valid_rate": round(sum(r["quiz_valid"] for r in rs) / len(rs), 2),
            "avg_weak_share": round(sum(shares) / len(shares), 2) if shares else None,
            "duplicate_questions": sum(r["quiz_duplicates"] for r in rs),
            "avg_quiz_attempts": round(sum(r["quiz_attempts"] for r in rs) / len(rs), 2),
        }
    summary["errors"] = sum(r["system"] == "error" for r in rows)
    iv = state["interviews"]
    summary["interviews"] = (
        {
            "cases": len(iv),
            "followup_relevance": round(sum(r["references_answer"] for r in iv) / len(iv), 2),
            "flagged_followup_rate": round(sum(r["flagged_followup"] for r in iv) / len(iv), 2),
        }
        if iv
        else None
    )
    c = state["consecutive"]
    summary["consecutive"] = (
        {
            k: c[k]
            for k in ("quizzes_per_topic", "baseline_duplicate_rate", "placementiq_duplicate_rate")
        }
        | {"topics": sorted(c["topics"])}
        if c
        else None
    )
    summary["agent_stats"] = [dict(r) for r in db.agent_stats()]
    return summary


def _write_csv(path: Path, data: list[dict]) -> None:
    if not data:
        return
    fields = list(dict.fromkeys(k for row in data for k in row))  # error rows have fewer keys
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(data)


def _save(results: Path, state: dict) -> None:
    (results / "state.json").write_text(json.dumps(state, indent=1), encoding="utf-8")
    _write_csv(results / "cases.csv", state["rows"])
    _write_csv(results / "questions.csv", state["questions"])
    _write_csv(results / "interviews.csv", state["interviews"])


def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--consecutive", type=int, default=0, metavar="N")
    ap.add_argument("--interviews", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--allow-mock", action="store_true", help="smoke-test only; results invalid")
    ap.add_argument("--results", type=Path, default=RESULTS_DIR)
    args = ap.parse_args(argv)

    args.results.mkdir(parents=True, exist_ok=True)
    state_file, eval_db = args.results / "state.json", args.results / "eval.db"
    if args.resume and state_file.exists():
        state = json.loads(state_file.read_text(encoding="utf-8"))
    else:
        state = _fresh_state()
        eval_db.unlink(missing_ok=True)  # agent_stats then cover this evaluation only
    os.environ["DB_PATH"] = str(eval_db)
    settings.cache_clear()
    mode = "mock" if settings().mock_mode else "live"
    if mode == "mock" and not args.allow_mock:
        raise SystemExit(
            "MOCK_MODE=true: results would be meaningless. Set MOCK_MODE=false "
            "or pass --allow-mock for a smoke test."
        )
    if state["mode"] not in (None, mode):
        raise SystemExit(f"--resume: the saved run is {state['mode']}, this one is {mode}")
    state["mode"] = mode
    db.init_db()

    cases = json.loads((HERE / "test_cases.json").read_text(encoding="utf-8"))["cases"]
    cases = cases[: args.limit]
    state["rows"] = [r for r in state["rows"] if r["system"] != "error"]  # failed cases retry
    done = {r["case"] for r in state["rows"]}
    probed = {r["case"] for r in state["interviews"]}
    stopped = None
    try:
        for case in cases:
            core_todo = case["id"] not in done
            probe_todo = args.interviews and case["id"] not in probed
            if not (core_todo or probe_todo):
                continue
            print(f"{case['id']} {case['target_role']} / {case['tag']} ...", flush=True)
            try:
                profile = agents.create_profile(case["resume_text"], case["target_role"])
                if core_todo:
                    _core(case, profile, state)
                if probe_todo:
                    state["interviews"].append(_interview_probe(case, profile))
            except llm.RateLimited as e:  # quota gone: later cases would fail the same way
                stopped = f"{case['id']}: {e}"
                print(f"  stopped early: {e}")
                break
            except (llm.LLMError, graph.CriticRejected) as e:
                print(f"  error: {e}")
                if core_todo and case["id"] not in {r["case"] for r in state["rows"]}:
                    state["rows"].append(
                        {
                            "case": case["id"],
                            "tag": case["tag"],
                            "system": "error",
                            "reasons": str(e),
                        }
                    )
            _save(args.results, state)  # checkpoint: a killed run resumes from here
        if args.consecutive and not stopped:
            topics = sorted({c["quiz_topic"] for c in cases})
            try:
                _consecutive(topics, args.consecutive, state, lambda: _save(args.results, state))
            except llm.RateLimited as e:
                stopped = f"consecutive quizzes: {e}"
                print(f"  stopped early: {e}")
    finally:
        _save(args.results, state)  # progress survives rate limits and crashes

    summary = _summary(state, stopped)
    (args.results / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "agent_stats"}, indent=2))
    return summary


if __name__ == "__main__":
    main()
