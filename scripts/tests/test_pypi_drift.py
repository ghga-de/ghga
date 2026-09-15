"""Tests for pypi_drift.py's decision which changed files ship.

A comment in `pyproject.toml` never reaches the wheel, so with `--base` a comment-only
edit must not demand a version bump. Everything else stays fail-closed.
"""

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pypi_drift

MEMBER = "tools/demo"
PYPROJECT = f"{MEMBER}/pyproject.toml"
README = f"{MEMBER}/README.md"
ORIGINAL = """\
# Capability markers (ADR-0014)
[project]
name = "demo"
version = "1.0.0"
"""


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A git repo with one lane member committed, wired in as the script's root."""
    (tmp_path / MEMBER).mkdir(parents=True)
    (tmp_path / PYPROJECT).write_text(ORIGINAL)
    (tmp_path / README).write_text("# demo\n")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(
        tmp_path,
        "-c", "user.name=test", "-c", "user.email=test@example.org",
        "commit", "-q", "-m", "base",
    )  # fmt: skip
    monkeypatch.setattr(pypi_drift, "ROOT", tmp_path)
    monkeypatch.setattr(
        pypi_drift, "pypi_members", lambda: [SimpleNamespace(path=MEMBER)]
    )
    monkeypatch.setattr(pypi_drift, "_packaged_roots", lambda path: ["src"])
    return tmp_path


def test_comment_only_pyproject_change_does_not_ship(repo):
    """Renumbering an ADR in a comment leaves the parsed TOML, and the wheel, unchanged."""
    base = _git(repo, "rev-parse", "HEAD")
    (repo / PYPROJECT).write_text(ORIGINAL.replace("ADR-0014", "ADR-0033"))
    assert pypi_drift.changed_members([PYPROJECT], base) == []


def test_pyproject_value_change_ships(repo):
    """A changed value is content, whatever the comments do."""
    base = _git(repo, "rev-parse", "HEAD")
    (repo / PYPROJECT).write_text(ORIGINAL.replace("1.0.0", "1.0.1"))
    assert pypi_drift.changed_members([PYPROJECT], base) == [MEMBER]


def test_without_base_any_pyproject_change_ships(repo):
    """Without a base there is nothing to compare against, so the change counts."""
    (repo / PYPROJECT).write_text(ORIGINAL.replace("ADR-0014", "ADR-0033"))
    assert pypi_drift.changed_members([PYPROJECT]) == [MEMBER]


def test_new_pyproject_ships(repo):
    """A file missing at the base cannot be compared, so it counts as changed."""
    (repo / PYPROJECT).write_text(ORIGINAL.replace("ADR-0014", "ADR-0033"))
    assert pypi_drift.changed_members(
        [PYPROJECT], "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    ) == [MEMBER]


def test_readme_change_still_ships(repo):
    """The README is the project description on PyPI, so any edit to it ships."""
    base = _git(repo, "rev-parse", "HEAD")
    (repo / README).write_text("# demo\n\nSee ADR-0033.\n")
    assert pypi_drift.changed_members([README], base) == [MEMBER]


def _readme_with_link(repo: Path, target: str) -> None:
    (repo / README).write_text(
        f"See [it](https://github.com/ghga-de/ghga/blob/main/{target}).\n"
    )


def test_link_to_existing_file_is_fine(repo):
    """A link that resolves in the tree is what the PyPI page needs."""
    _readme_with_link(repo, PYPROJECT)
    assert pypi_drift.readme_link_problems(MEMBER) == []


def test_link_to_missing_file_is_reported(repo):
    """A renamed or deleted target would 404 on the PyPI page."""
    _readme_with_link(repo, "docs/gone.md")
    problems = pypi_drift.readme_link_problems(MEMBER)
    assert len(problems) == 1
    assert "docs/gone.md" in problems[0]


def test_link_to_moved_stub_is_reported(repo):
    """A stub keeps old releases working, but a new release must link past it."""
    (repo / "docs").mkdir()
    (repo / "docs/old.md").write_text("<!-- moved: docs/new.md -->\n# Moved\n")
    _readme_with_link(repo, "docs/old.md")
    problems = pypi_drift.readme_link_problems(MEMBER)
    assert len(problems) == 1
    assert "moved" in problems[0]


def test_link_anchor_and_trailing_slash_are_ignored(repo):
    """Anchors and directory links resolve like the path they name."""
    (repo / README).write_text(
        "[a](https://github.com/ghga-de/ghga/blob/main/tools/demo/pyproject.toml#L1)"
        " [b](https://github.com/ghga-de/ghga/tree/main/tools/demo/)\n"
    )
    assert pypi_drift.readme_link_problems(MEMBER) == []
