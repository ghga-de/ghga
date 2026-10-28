"""Tests for affected_targets.py: a missing base ref, and the change set it reads.

The default base is `origin/dev` (ADR-0038), a remote-tracking ref that a clone which has
not fetched since `dev` was created simply does not have. Answering that from the working
tree would report "nothing affected" for a branch whose work is committed — the tree is
clean, so the fallback saw an empty change set it had never looked at.

With a base that resolves, the change set is the branch's commits plus whatever the
working tree adds, so a change is seen before it is committed.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "affected_targets.py"
sys.path.insert(0, str(SCRIPT.parent))

import affected_targets

MISSING = "origin/no-such-ref-for-tests"


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True
    )


def test_missing_base_fails_instead_of_reporting_nothing():
    """A base that does not resolve is an error, never an empty target list."""
    result = _run("--base", MISSING)
    assert result.returncode != 0
    assert MISSING in result.stderr
    assert result.stdout.strip() == ""


def test_missing_base_names_the_fetch_that_fixes_it():
    """`origin/<branch>` is the common failure, so the message says how to resolve it."""
    result = _run("--base", MISSING)
    assert "git fetch origin no-such-ref-for-tests" in result.stderr
    assert "--all" in result.stderr


def test_non_origin_base_omits_the_fetch_hint():
    """`git fetch origin HEAD~1` is not advice; only remote-tracking refs get that hint."""
    result = _run("--base", "no-such-local-ref")
    assert result.returncode != 0
    assert "git fetch" not in result.stderr
    assert "--all" in result.stderr


def test_all_needs_no_base():
    """--all skips diffing, so a missing base ref cannot affect it."""
    result = _run("--all", "--base", MISSING)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["all"] is True
    assert payload["targets"]


def test_a_file_in_a_target_root_is_not_a_target():
    """`libs/AGENTS.md` is a file in `libs/`, not a member directory called AGENTS.md."""
    is_all, targets = affected_targets.affected(
        ["libs/AGENTS.md", "libs/CLAUDE.md", "services/AGENTS.md"]
    )
    assert not is_all
    assert targets == []


# --- the change set, in a throwaway repo ------------------------------------------------


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repo with two libs, `b` depending on `a`, on a branch with one commit of its own.

    `base` marks where the branch was cut; the branch commit touches neither lib.
    """
    for name, deps in (("a", []), ("b", ["a"])):
        member = tmp_path / "libs" / name
        member.mkdir(parents=True)
        (member / "pyproject.toml").write_text(
            f'[project]\nname = "{name}"\ndependencies = {json.dumps(deps)}\n'
        )
    (tmp_path / ".gitignore").write_text("*.log\n")
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "base")
    _git(tmp_path, "tag", "base")
    (tmp_path / "notes.txt").write_text("not in any target\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "work")
    monkeypatch.setattr(affected_targets, "REPO", tmp_path)
    return tmp_path


def _verdict() -> tuple[bool, list[str]]:
    """What the branch affects: (everything?, the affected targets).

    The flag is True only when a repo-wide file changed; the targets are the member
    directories the change set reaches, dependents included.
    """
    return affected_targets.affected(affected_targets.changed_files("base"))


def test_a_clean_tree_reports_only_the_committed_change(branch: Path):
    """With nothing uncommitted, the change set is the three-dot diff it always was."""
    assert affected_targets.changed_files("base") == ["notes.txt"]
    assert _verdict() == (False, [])


@pytest.mark.parametrize("staged", [False, True])
def test_an_uncommitted_edit_is_affected(branch: Path, staged: bool):
    """An edit counts before it is committed, staged or not, and takes its dependents."""
    (branch / "libs/a/pyproject.toml").write_text('[project]\nname = "a"\n')
    if staged:
        _git(branch, "add", ".")
    assert _verdict() == (False, ["libs/a", "libs/b"])


def test_an_untracked_file_is_affected(branch: Path):
    """A new file counts before it is added; an ignored one does not."""
    (branch / "libs/b/module.py").write_text("")
    (branch / "libs/a/run.log").write_text("")
    assert affected_targets.changed_files("base") == ["libs/b/module.py", "notes.txt"]
    assert _verdict() == (False, ["libs/b"])
