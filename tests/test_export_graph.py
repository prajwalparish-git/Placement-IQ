from scripts import export_graph


def test_export_writes_raw_and_github_renderable_mermaid(tmp_path):
    mmd, md = export_graph.main(["--out", str(tmp_path)])
    raw = mmd.read_text(encoding="utf-8")
    assert "generate" in raw and "verify" in raw and "retry" in raw
    text = md.read_text(encoding="utf-8")
    assert text.count("```") == 2 and "```mermaid" in text
    assert "<p>" not in text and "config:" not in text  # front matter and HTML labels removed
    assert "__start__([start])" in text and "__end__([end])" in text  # clean labels


def test_docs_copy_is_up_to_date():
    from piq.config import ROOT

    committed = (ROOT / "docs" / "critic_graph.md").read_text(encoding="utf-8")
    raw = (ROOT / "docs" / "critic_graph.mmd").read_text(encoding="utf-8")
    assert committed == export_graph._for_markdown(raw)  # regenerate with scripts.export_graph
