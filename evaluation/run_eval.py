"""Baseline (one prompt) vs PlacementIQ (agents + critic) on the frozen test set.

    python -m evaluation.run_eval [--limit N] [--allow-mock] [--results DIR]

Both systems are scored by the same deterministic checks and the same LLM critic.
Writes to evaluation/results/: cases.csv, questions.csv (for manual labelling),
summary.json, and a fresh eval.db so the app database is untouched.
Quota: ~6-10 Groq calls per case.
"""

import argparse
import csv
import json
import os
from pathlib import Path

from piq import agents, checks, db, graph, llm, prompts
from piq.config import QUIZ_SIZE, settings
from piq.schemas import BaselineOutput

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"


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


def _summary(rows: list[dict], mode: str) -> dict:
    summary: dict = {"mode": mode}
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


def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--allow-mock", action="store_true", help="smoke-test only; results invalid")
    ap.add_argument("--results", type=Path, default=RESULTS)
    args = ap.parse_args(argv)

    args.results.mkdir(parents=True, exist_ok=True)
    eval_db = args.results / "eval.db"
    eval_db.unlink(missing_ok=True)  # every run starts clean, so agent_stats cover this run only
    os.environ["DB_PATH"] = str(eval_db)
    settings.cache_clear()
    mode = "mock" if settings().mock_mode else "live"
    if mode == "mock" and not args.allow_mock:
        raise SystemExit(
            "MOCK_MODE=true: results would be meaningless. Set MOCK_MODE=false "
            "or pass --allow-mock for a smoke test."
        )
    db.init_db()

    cases = json.loads((HERE / "test_cases.json").read_text(encoding="utf-8"))["cases"]
    rows, questions = [], []
    for case in cases[: args.limit]:
        print(f"{case['id']} {case['target_role']} / {case['tag']} ...", flush=True)
        try:
            profile = agents.create_profile(case["resume_text"], case["target_role"])
            weakness = checks.topic_weakness(case["scores"], agents.missing_topics(profile))
            q_inp = agents.quiz_inputs(
                case["quiz_topic"], case["difficulty"], case["previous_questions"]
            )

            base = _baseline(case)
            rows.append(_row(case, "baseline", base.plan, base.quiz, weakness, q_inp))

            p = graph.run(
                agents.PLANNER_TASK, agents.planner_inputs(profile, case["scores"], case["week_no"])
            )
            q = graph.run(agents.QUIZ_TASK, q_inp)
            rows.append(
                _row(
                    case,
                    "placementiq",
                    p.output,
                    q.output,
                    weakness,
                    q_inp,
                    (p.attempts, q.attempts),
                )
            )
            for system, quiz in (("baseline", base.quiz), ("placementiq", q.output)):
                questions += [
                    {
                        "case": case["id"],
                        "system": system,
                        "topic": quiz.topic,
                        "text": qq.text,
                        "options": " || ".join(qq.options),
                        "marked": qq.correct_index,
                        "label_valid (y/n)": "",
                    }
                    for qq in quiz.questions
                ]
        except (llm.LLMError, graph.CriticRejected) as e:
            print(f"  error: {e}")
            rows.append(
                {"case": case["id"], "tag": case["tag"], "system": "error", "reasons": str(e)}
            )

    _write_csv(args.results / "cases.csv", rows)
    _write_csv(args.results / "questions.csv", questions)
    summary = _summary(rows, mode)
    (args.results / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "agent_stats"}, indent=2))
    return summary


if __name__ == "__main__":
    main()
