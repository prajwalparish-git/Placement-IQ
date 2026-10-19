"""Write the compiled critic graph as Mermaid for the report.

    python -m scripts.export_graph            # -> docs/critic_graph.mmd and critic_graph.md
    python -m scripts.export_graph --png      # also PNG (renders via the mermaid.ink web API)

critic_graph.md wraps the diagram in a ```mermaid block, which GitHub renders.
"""

import argparse
import re
from pathlib import Path

from piq.config import ROOT
from piq.graph import Task, build


def _for_markdown(mermaid: str) -> str:
    """Drop the front-matter config and HTML labels that some renderers show literally."""
    body = re.sub(r"\A---\n.*?\n---\n", "", mermaid, flags=re.S)
    body = re.sub(r"<p>(.*?)</p>", lambda m: m[1].strip("_"), body)
    return (
        "# Critic loop (generated)\n\n"
        "Generated from the compiled LangGraph by `python -m scripts.export_graph`; "
        "do not edit by hand.\n\n```mermaid\n" + body.strip() + "\n```\n"
    )


def main(argv: list[str] | None = None) -> list[Path]:
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", action="store_true")
    ap.add_argument("--out", type=Path, default=ROOT / "docs")
    args = ap.parse_args(argv)
    graph = build(Task("example", lambda *_: (None, 0), lambda *_: [])).get_graph()
    args.out.mkdir(parents=True, exist_ok=True)
    mermaid = graph.draw_mermaid()
    written = [args.out / "critic_graph.mmd", args.out / "critic_graph.md"]
    written[0].write_text(mermaid, encoding="utf-8")
    written[1].write_text(_for_markdown(mermaid), encoding="utf-8")
    if args.png:
        written.append(args.out / "critic_graph.png")
        written[-1].write_bytes(graph.draw_mermaid_png())
    for path in written:
        print(f"wrote {path}")
    return written


if __name__ == "__main__":
    main()
