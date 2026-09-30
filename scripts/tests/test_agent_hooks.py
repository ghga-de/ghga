"""Tests for the agent hooks registered in .claude/settings.json."""

import io
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

import pytest

HOOKS = Path(__file__).resolve().parents[1] / "agent_hooks"
REPO = HOOKS.parents[1]
sys.path.insert(0, str(HOOKS))

import container_check
import format_python
import guard_generated
import guard_uv
import host


@pytest.fixture
def on_the_host(monkeypatch, tmp_path):
    """Simulate a session on the host: no /.dockerenv, no exemption."""
    monkeypatch.setattr(host, "DOCKERENV", tmp_path / "no-dockerenv")
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GHGA_ALLOW_HOST", raising=False)


@pytest.fixture
def in_container(monkeypatch, tmp_path):
    """Simulate a session in the dev container."""
    dockerenv = tmp_path / ".dockerenv"
    dockerenv.touch()
    monkeypatch.setattr(host, "DOCKERENV", dockerenv)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GHGA_ALLOW_HOST", raising=False)


def _stdin(monkeypatch, payload):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))


@pytest.mark.usefixtures("on_the_host")
@pytest.mark.parametrize("variable", ["CI", "GHGA_ALLOW_HOST"])
def test_exemptions_count_as_not_on_host(monkeypatch, variable):
    assert host.on_host()
    monkeypatch.setenv(variable, "1")
    assert not host.on_host()


@pytest.mark.usefixtures("in_container")
def test_container_is_not_host():
    assert not host.on_host()


@pytest.mark.parametrize(
    "command",
    [
        "uv sync",
        "uv",
        "uv run pytest",
        "cd libs/hexkit && uv run pytest",
        "true; uv lock",
        "UV_PYTHON=3.12 uv venv",
        "echo $(uv --version)",
        "(uv sync)",
        'bash -c "uv sync"',
        "sh -c 'uv lock'",
        "env uv sync",
        "time uv run pytest",
        "echo libs/hexkit | xargs uv build",
        "sudo uv pip install x",
        "echo uv",  # a false match, accepted because the hook acts only on the host
    ],
)
def test_runs_uv(command):
    assert guard_uv.runs_uv(command)


@pytest.mark.parametrize(
    "command",
    [
        "just sync",
        "uvx ruff",
        "ls .venv/uv",
        "cat uv.lock",
        "rg -n uv_ justfile",
    ],
)
def test_does_not_run_uv(command):
    assert not guard_uv.runs_uv(command)


@pytest.mark.usefixtures("on_the_host")
def test_uv_blocked_on_host(monkeypatch, capsys):
    _stdin(monkeypatch, {"tool_input": {"command": "uv sync"}})
    assert guard_uv.main() == 2
    assert "just" in capsys.readouterr().err


@pytest.mark.usefixtures("in_container")
def test_uv_allowed_in_container(monkeypatch, capsys):
    _stdin(monkeypatch, {"tool_input": {"command": "uv sync"}})
    assert guard_uv.main() == 0
    assert capsys.readouterr() == ("", "")


@pytest.mark.usefixtures("on_the_host")
def test_container_check_warns_on_host(capsys):
    assert container_check.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert "outside the dev container" in output["systemMessage"]
    specific = output["hookSpecificOutput"]
    assert specific["hookEventName"] == "SessionStart"
    assert "ask before" in specific["additionalContext"]


@pytest.mark.usefixtures("in_container")
def test_container_check_silent_in_container(capsys):
    assert container_check.main() == 0
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize(
    ("rel", "how"),
    [
        ("uv.lock", "just lock"),
        ("frontend/data-portal/pnpm-lock.yaml", "pnpm install"),
        ("deploy/charts/ghga-demo/values-mono.yaml", "just charts"),
        ("deploy/charts/ghga-demo/values-artifacts.yaml", "just testbed-artifacts"),
        ("deploy/charts/auth-service/values.yaml", "just charts"),
        ("deploy/charts/test-oidc-provider/templates/x.yaml", "just charts"),
    ],
)
def test_generated_files(rel, how):
    assert how in (guard_generated.regenerate_with(PurePosixPath(rel)) or "")


@pytest.mark.parametrize(
    "rel",
    [
        "deploy/charts/aai/values.yaml",
        "deploy/charts/ghga-demo/values.yaml",
        "deploy/charts/ghga-common/values.yaml",
        "deploy/src/create_charts.py",
        "services/auth-service/chart-values.yaml",
        "libs/hexkit/uv.lock",
    ],
)
def test_hand_edited_files(rel):
    assert guard_generated.regenerate_with(PurePosixPath(rel)) is None


def test_checkout_of_worktree(tmp_path):
    """A worktree has a .git file rather than a directory."""
    (tmp_path / ".git").write_text("gitdir: elsewhere\n")
    assert guard_generated.checkout_of(tmp_path / "deploy/charts/ars/Chart.yaml") == (
        tmp_path
    )


def test_service_doc_names_match_the_generator():
    sys.path.insert(0, str(REPO / "scripts"))
    import service_docs

    assert service_docs.MEMBER_GLOBS == tuple(
        f"{tier}/*" for tier in guard_generated.MEMBER_TIERS
    )
    assert (
        guard_generated.SCHEMA_FILE,
        guard_generated.EXAMPLE_FILE,
        guard_generated.OPENAPI_FILE,
    ) == (
        service_docs.SCHEMA_FILE,
        service_docs.EXAMPLE_FILE,
        service_docs.OPENAPI_FILE,
    )


@pytest.mark.parametrize(
    "rel",
    [
        "services/ucs/config_schema.json",
        "services/ucs/example_config.yaml",
        "services/ucs/openapi.yaml",
        "libs/metldata/example_config.yaml",
        "tools/ghga-connector/config_schema.json",
    ],
)
def test_service_docs_blocked(rel):
    assert "just service-docs" in (
        guard_generated.regenerate_with(PurePosixPath(rel)) or ""
    )


@pytest.mark.parametrize(
    "rel",
    [
        "tools/ghga-datasteward-kit/example_config.yaml",  # no config schema: by hand
        "services/ifrs/openapi.yaml",  # no REST API, so none to regenerate
        "services/ucs/dev_config.yaml",
        "services/ucs/README.md",  # the parameter list is left to the pre-commit hook
        "services/ucs/tests/fixtures/example_config.yaml",
        "example_config.yaml",
    ],
)
def test_service_docs_hand_edited(rel):
    assert guard_generated.regenerate_with(PurePosixPath(rel)) is None


@pytest.fixture
def checkout(monkeypatch, tmp_path):
    """A checkout with its own ruff and the repo's config, standing in for the repo."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text((REPO / "pyproject.toml").read_text())
    bin_dir = tmp_path / ".venv" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "ruff").symlink_to(Path(sys.executable).parent / "ruff")
    monkeypatch.setattr(format_python, "REPO", tmp_path)
    return tmp_path


UNFORMATTED = "import sys\nimport os\nx = {'a':1}\n"


def _format(monkeypatch, path):
    _stdin(monkeypatch, {"tool_name": "Edit", "tool_input": {"file_path": str(path)}})
    return format_python.main()


@pytest.mark.usefixtures("in_container")
def test_format_python_file(monkeypatch, capsys, checkout):
    path = checkout / "pkg" / "module.py"
    path.parent.mkdir()
    path.write_text(UNFORMATTED)
    assert _format(monkeypatch, path) == 0
    # formatted, imports sorted, the unused imports left for `just lint` to report
    assert path.read_text() == 'import os\nimport sys\n\nx = {"a": 1}\n'
    assert capsys.readouterr() == ("", "")


@pytest.mark.usefixtures("in_container")
def test_format_skips_non_python(monkeypatch, checkout):
    path = checkout / "notes.txt"
    path.write_text(UNFORMATTED)
    assert _format(monkeypatch, path) == 0
    assert path.read_text() == UNFORMATTED


@pytest.mark.usefixtures("in_container")
def test_format_skips_outside_repo(monkeypatch, checkout):
    monkeypatch.setattr(format_python, "REPO", checkout / "elsewhere")
    path = checkout / "module.py"
    path.write_text(UNFORMATTED)
    assert _format(monkeypatch, path) == 0
    assert path.read_text() == UNFORMATTED


@pytest.mark.usefixtures("in_container")
def test_format_skips_without_ruff(monkeypatch, checkout):
    (checkout / ".venv" / "bin" / "ruff").unlink()
    path = checkout / "module.py"
    path.write_text(UNFORMATTED)
    assert _format(monkeypatch, path) == 0
    assert path.read_text() == UNFORMATTED


@pytest.mark.usefixtures("on_the_host")
def test_format_skips_on_host(monkeypatch, checkout):
    path = checkout / "module.py"
    path.write_text(UNFORMATTED)
    assert _format(monkeypatch, path) == 0
    assert path.read_text() == UNFORMATTED


def _run(script, payload, **env):
    return subprocess.run(
        [sys.executable, str(HOOKS / script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", **env},
        check=False,
    )


def test_generated_hook_as_registered():
    """Run as the settings do, as a script with the hook JSON on stdin."""
    result = _run(
        "guard_generated.py", {"tool_input": {"file_path": str(REPO / "uv.lock")}}
    )
    assert result.returncode == 2
    assert "just lock" in result.stderr
    result = _run(
        "guard_generated.py", {"tool_input": {"file_path": str(REPO / "README.md")}}
    )
    assert (result.returncode, result.stderr) == (0, "")


def test_uv_hook_exempt_in_ci():
    result = _run("guard_uv.py", {"tool_input": {"command": "uv sync"}}, CI="true")
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


def test_container_check_silent_in_ci():
    result = _run("container_check.py", {"source": "startup"}, CI="true")
    assert (result.returncode, result.stdout) == (0, "")


def test_format_hook_as_registered():
    result = _run(
        "format_python.py", {"tool_input": {"file_path": str(REPO / "README.md")}}
    )
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")
