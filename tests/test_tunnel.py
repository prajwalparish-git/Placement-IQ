"""The demo tunnel lifts Streamlit's same-origin checks for its own process only."""

import tomllib

from piq.config import ROOT

SCRIPTS = ROOT / "scripts"


def test_config_toml_keeps_cors_and_xsrf_protection_on():
    config = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    server = config["server"]
    assert server.get("enableCORS", True) is True
    assert server.get("enableXsrfProtection", True) is True


def test_tunnel_script_lifts_the_checks_on_the_command_line():
    ps1 = (SCRIPTS / "tunnel.ps1").read_text(encoding="utf-8")
    assert '"--server.enableCORS", "false"' in ps1
    assert '"--server.enableXsrfProtection", "false"' in ps1
    assert "cloudflared tunnel --url" in ps1
    assert "Stop-Process" in ps1  # the Streamlit it started ends with the tunnel


def test_tunnel_bat_runs_the_powershell_script():
    bat = (SCRIPTS / "tunnel.bat").read_text(encoding="utf-8")
    assert '-File "%~dp0tunnel.ps1"' in bat
