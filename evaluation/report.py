"""Turn evaluation/results/summary.json into report.md (tables) and chart.svg for the report.

    python -m evaluation.report [--results DIR]

The SVG can be inserted directly into Word or PowerPoint; no plotting library needed.
"""

import argparse
import json
from pathlib import Path

from piq import formatter
from piq.config import RESULTS_DIR


def main(argv: list[str] | None = None) -> list[Path]:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, default=RESULTS_DIR)
    args = ap.parse_args(argv)
    source = args.results / "summary.json"
    if not source.exists():
        raise SystemExit(f"{source} not found: run python -m evaluation.run_eval first")
    summary = json.loads(source.read_text(encoding="utf-8"))
    md, svg = args.results / "report.md", args.results / "chart.svg"
    md.write_text(formatter.results_md(summary), encoding="utf-8")
    svg.write_text(formatter.results_svg(formatter.results_table(summary)), encoding="utf-8")
    print(f"wrote {md}\nwrote {svg}")
    return [md, svg]


if __name__ == "__main__":
    main()
