"""Write the compiled critic graph as Mermaid source for the report.

python -m scripts.export_graph            # -> docs/critic_graph.mmd
python -m scripts.export_graph --png      # also PNG (renders via the mermaid.ink web API)
"""

import sys

from piq.config import ROOT
from piq.graph import Task, build


def main() -> None:
    graph = build(Task("example", lambda *_: (None, 0), lambda *_: [])).get_graph()
    out = ROOT / "docs"
    out.mkdir(exist_ok=True)
    (out / "critic_graph.mmd").write_text(graph.draw_mermaid(), encoding="utf-8")
    print(f"wrote {out / 'critic_graph.mmd'}")
    if "--png" in sys.argv:
        (out / "critic_graph.png").write_bytes(graph.draw_mermaid_png())
        print(f"wrote {out / 'critic_graph.png'}")


if __name__ == "__main__":
    main()
