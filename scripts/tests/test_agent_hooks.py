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
import git_hooks_check
import guard_bypass
import guard_generated
import guard_lint_config
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


def test_generated_hook_reads_notebook_path():
    result = _run(
        "guard_generated.py", {"tool_input": {"notebook_path": str(REPO / "uv.lock")}}
    )
    assert result.returncode == 2


def test_uv_hook_exempt_in_ci():
    result = _run("guard_uv.py", {"tool_input": {"command": "uv sync"}}, CI="true")
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


def test_container_check_silent_in_ci():
    result = _run("container_check.py", {"source": "startup"}, CI="true")
    assert (result.returncode, result.stdout) == (0, "")


@pytest.mark.parametrize(
    ("command", "what"),
    [
        ("git commit --no-verify -m x", "--no-verify"),
        ("git commit -nm x", "-n"),
        ("git commit -an", "-n"),
        ("git push --no-verify", "--no-verify"),
        ("cd a && git -c core.hooksPath=/dev/null commit", "core.hooksPath"),
        ("git -c CORE.HOOKSPATH=x commit", "HOOKSPATH"),
        ("git --config-env=core.hooksPath=X commit", "core.hooksPath"),
        ("git config core.hooksPath /tmp/none", "core.hooksPath"),
        ("git config set --local core.hooksPath x", "core.hooksPath"),
        ("SKIP=mypy git commit -m x", "SKIP"),
        ("env SKIP=ruff git commit -m x", "SKIP"),
        ("export SKIP=ruff", "SKIP"),
        ("true\nexport SKIP=ruff", "SKIP"),
        ('bash -c "git commit --no-verify"', "--no-verify"),
        ("sh -lc 'git commit -n'", "-n"),
        ("eval git commit --no-verify", "--no-verify"),
        ("pre-commit uninstall", "uninstall"),
        ("uv run pre-commit uninstall", "uninstall"),
        ("git commit -m 'unbalanced --no-verify", "--no-verify"),
        ("cat <<EOF\ntext\nEOF\ngit commit --no-verify", "--no-verify"),
    ],
)
def test_bypass_blocked(command, what):
    assert what in (guard_bypass.bypass(command) or "")


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m x",
        "git commit -mn",  # "n" is the message
        "git commit -am 'mention -n and --no-verify'",
        "git commit -m -n",
        "git push -n",  # a dry run, not --no-verify
        "git merge -n dev",
        "git config core.hooksPath",
        "git config --get core.hooksPath",
        "git config --unset core.hooksPath",
        "rg -- --no-verify docs",
        "rg -n 'SKIP=' justfile",
        "SKIP=no-commit-to-branch uv run pre-commit run --all-files",
        "just hooks-all",
        "git log --oneline | head",
        "git commit -F - <<'EOF'\ndon't use --no-verify\nEOF",
        "git commit -m \"$(cat <<'EOF'\nBlock SKIP= and --no-verify, don't allow\nEOF\n)\"",
        "git commit -F- <<-EOF\n\tit's -n\n\tEOF",
    ],
)
def test_bypass_allowed(command):
    assert guard_bypass.bypass(command) is None


def test_bypass_hook_as_registered():
    result = _run(
        "guard_bypass.py", {"tool_input": {"command": "git commit --no-verify"}}
    )
    assert result.returncode == 2
    assert "ask the dev" in result.stderr
    result = _run("guard_bypass.py", {"tool_input": {"command": "git status"}})
    assert (result.returncode, result.stderr) == (0, "")


@pytest.fixture
def checkout(tmp_path):
    """A checkout with a root pyproject.toml holding check and dependency tables."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["a"]\n\n[tool.ruff]\nline-length = 88\n'
    )
    return tmp_path


def _asks(path, **tool_input):
    """The reason the lint-config hook asks for, or None when it lets the edit pass."""
    payload = {"tool_input": {"file_path": str(path), **tool_input}}
    result = _run("guard_lint_config.py", payload)
    assert result.returncode == 0
    if not result.stdout:
        return None
    output = json.loads(result.stdout)["hookSpecificOutput"]
    assert output["permissionDecision"] == "ask"
    return output["permissionDecisionReason"]


def test_changed_tables_names_only_check_tables():
    before = "[tool.ruff]\nx = 1\n[tool.pytest.ini_options]\ny = 1\n[tool.uv]\nz = 1\n"
    after = "[tool.ruff]\nx = 1\n[tool.pytest.ini_options]\ny = 2\n[tool.uv]\nz = 2\n"
    assert guard_lint_config.changed_tables(before, after) == ["pytest"]


def test_lint_config_asks_for_check_tables(checkout):
    reason = _asks(
        checkout / "pyproject.toml",
        old_string="line-length = 88",
        new_string="line-length = 120",
    )
    assert "[tool.ruff]" in reason


def test_lint_config_asks_for_a_new_member_table(checkout):
    member = checkout / "services/x/pyproject.toml"
    member.parent.mkdir(parents=True)
    member.write_text('[project]\nname = "x"\n')
    content = '[project]\nname = "x"\n\n[tool.mypy]\nstrict = false\n'
    assert "[tool.mypy]" in _asks(member, content=content)


def test_lint_config_lets_dependencies_pass(checkout):
    path = checkout / "pyproject.toml"
    assert _asks(path, old_string='["a"]', new_string='["a", "b"]') is None


def test_lint_config_asks_when_toml_breaks(checkout):
    path = checkout / "pyproject.toml"
    reason = _asks(path, old_string="[tool.ruff]", new_string="[")
    assert "could not be compared" in reason


@pytest.mark.parametrize(
    "rel",
    [
        ".pre-commit-config.yaml",
        "ruff.toml",
        "libs/x/mypy.ini",
        "frontend/data-portal/eslint.config.js",
        "frontend/data-portal/.prettierrc",
        "frontend/data-portal/.prettierignore",
        "frontend/data-portal/eslint-local-rules/no-x.js",
    ],
)
def test_lint_config_asks_for_config_files(checkout, rel):
    assert rel in _asks(checkout / rel, content="x")


@pytest.mark.parametrize(
    "rel", ["README.md", "frontend/data-portal/tsconfig.json", "ruff_notes.md"]
)
def test_lint_config_lets_other_files_pass(checkout, rel):
    assert _asks(checkout / rel, content="x") is None


GIT_ENV = {
    "PATH": "/usr/bin:/bin",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_AUTHOR_NAME": "x",
    "GIT_AUTHOR_EMAIL": "x@example.org",
    "GIT_COMMITTER_NAME": "x",
    "GIT_COMMITTER_EMAIL": "x@example.org",
}


def _git(*args):
    subprocess.run(["git", *args], check=True, capture_output=True, env=GIT_ENV)


@pytest.mark.usefixtures("in_container")
def test_git_hooks_check_warns_when_missing(monkeypatch, tmp_path, capsys):
    _git("init", "-q", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    assert git_hooks_check.main() == 0
    assert "just hooks" in json.loads(capsys.readouterr().out)["systemMessage"]
    (tmp_path / ".git/hooks/pre-commit").write_text("#!/bin/sh\n")
    assert git_hooks_check.main() == 0
    assert capsys.readouterr() == ("", "")


@pytest.mark.usefixtures("in_container")
def test_git_hooks_check_finds_the_hook_from_a_worktree(monkeypatch, tmp_path, capsys):
    main, worktree = tmp_path / "main", tmp_path / "wt"
    _git("init", "-q", str(main))
    _git("-C", str(main), "commit", "-q", "--allow-empty", "-m", "x")
    _git("-C", str(main), "worktree", "add", "-q", str(worktree))
    (main / ".git/hooks/pre-commit").write_text("#!/bin/sh\n")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(worktree))
    assert git_hooks_check.main() == 0
    assert capsys.readouterr() == ("", "")


@pytest.mark.usefixtures("on_the_host")
def test_git_hooks_check_silent_on_host(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    assert git_hooks_check.main() == 0
    assert capsys.readouterr() == ("", "")
