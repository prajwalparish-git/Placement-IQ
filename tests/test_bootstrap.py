"""bootstrap.py: platform detection, the pinned uv build, the launchers it writes, .env
handling and the closing message. Nothing here downloads or installs anything."""

import ast
import shutil
import subprocess
from pathlib import Path

import pytest

import bootstrap
from piq.config import ROOT


def test_runs_on_old_pythons():
    """The script must start on Python 3.8 so it can install 3.13 from an older one."""
    ast.parse((ROOT / "bootstrap.py").read_text(encoding="utf-8"), feature_version=(3, 8))


def test_uses_the_standard_library_only():
    tree = ast.parse((ROOT / "bootstrap.py").read_text(encoding="utf-8"))
    imported = {
        (n.module if isinstance(n, ast.ImportFrom) else a.name).split(".")[0]
        for n in ast.walk(tree)
        if isinstance(n, ast.Import | ast.ImportFrom)
        for a in (n.names if isinstance(n, ast.Import) else [n])
    }
    import sys

    assert imported <= set(sys.stdlib_module_names) | {"__future__"}


@pytest.mark.parametrize(
    ("raw", "name"),
    [("Windows", "windows"), ("Darwin", "macos"), ("Linux", "linux"), ("FreeBSD", "linux")],
)
def test_system_name(raw, name):
    assert bootstrap.system_name(raw) == name


@pytest.mark.parametrize(
    ("raw", "name"), [("AMD64", "x86_64"), ("x86_64", "x86_64"), ("arm64", "aarch64")]
)
def test_arch_name(raw, name):
    assert bootstrap.arch_name(raw) == name


def test_every_supported_platform_has_a_pinned_checksum():
    for system in ("windows", "macos", "linux"):
        for arch in ("x86_64", "aarch64"):
            asset = bootstrap.uv_asset(system, arch)
            assert len(bootstrap.UV_SHA256[asset]) == 64
    with pytest.raises(ValueError, match="no pinned uv build"):
        bootstrap.uv_asset("linux", "riscv64")


def test_archive_paths_are_checked():
    bootstrap._safe_members(["uv-x86_64/uv", "uv.exe"])
    for bad in ("../evil", "/etc/passwd", "a/../../b"):
        with pytest.raises(ValueError, match="unsafe"):
            bootstrap._safe_members([bad])


def test_venv_python_path():
    assert bootstrap.venv_python(Path("v"), "windows") == Path("v/Scripts/python.exe")
    assert bootstrap.venv_python(Path("v"), "macos") == Path("v/bin/python")


@pytest.mark.parametrize(
    ("system", "name"), [("windows", "run.ps1"), ("macos", "run.sh"), ("linux", "run.sh")]
)
def test_launcher_per_system(tmp_path, system, name):
    path = bootstrap.write_launcher(system, tmp_path)
    assert path.name == name
    body = path.read_bytes()
    assert (b"\r\n" in body) == (system == "windows")  # PowerShell CRLF, sh LF
    text = body.decode("utf-8")
    for command in ("app", "api", "seed", "test", "check"):
        assert command in text
    assert "streamlit run app.py" in text and "bootstrap.py" in text


@pytest.mark.skipif(shutil.which("sh") is None, reason="no POSIX shell")
def test_run_sh_is_valid_shell(tmp_path):
    path = bootstrap.write_launcher("linux", tmp_path)
    assert subprocess.run(["sh", "-n", str(path)], capture_output=True).returncode == 0


def test_env_file_is_created_once_and_never_overwritten(tmp_path):
    (tmp_path / ".env.example").write_text("MOCK_MODE=true\n", encoding="utf-8")
    assert bootstrap.ensure_env_file(tmp_path) is True
    (tmp_path / ".env").write_text("GEMINI_API_KEY=mine\n", encoding="utf-8")
    assert bootstrap.ensure_env_file(tmp_path) is False
    assert (tmp_path / ".env").read_text(encoding="utf-8") == "GEMINI_API_KEY=mine\n"


def test_env_status_reports_filled_keys_never_values(tmp_path):
    (tmp_path / ".env").write_text(
        "# GEMINI_API_KEY=commented\nGEMINI_API_KEY=\nGROQ_API_KEY_1=k1\nMOCK_MODE=false\n",
        encoding="utf-8",
    )
    status = bootstrap.env_status(tmp_path)
    assert status["GEMINI_API_KEY"] is False and status["GROQ_API_KEY"] is True
    assert status["MOCK_MODE=false"] is True and status["DATABASE_URL"] is False
    message = bootstrap.summary("windows", made_env=False, root=tmp_path)
    assert "k1" not in message  # a key's value is never printed
    assert r".\run.ps1" in message and "ExecutionPolicy Bypass" in message


def test_summary_names_the_run_command_per_system(tmp_path):
    assert "./run.sh" in bootstrap.summary("macos", made_env=True, root=tmp_path)
    assert "created just now" in bootstrap.summary("linux", made_env=True, root=tmp_path)


def test_generated_files_and_tools_are_git_ignored():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for entry in ("/run.sh", "/run.ps1", ".tools/", ".venv/", ".env"):
        assert entry in ignored
