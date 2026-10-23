"""The CI workflow's own guarantees (read as text: no YAML parser is installed)."""

from piq.config import ROOT


def test_ci_token_can_only_read_the_repository():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    top = ci.split("\njobs:", 1)[0]  # top level, so it covers every job
    assert "\npermissions:\n  contents: read\n" in top
