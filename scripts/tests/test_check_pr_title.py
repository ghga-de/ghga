"""Tests for check_pr_title.py: which titles pass the naming grammar, and how it warns."""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from check_pr_title import is_exempt, title_problems

CHECK = Path(__file__).resolve().parents[1] / "check_pr_title.py"


@pytest.mark.parametrize(
    "title",
    [
        "[upload] Add UCS endpoints (GSI-1234)",
        "[pr-skills] Check PR titles (GSI-2540)",
        "Add UCS endpoints (GSI-1234)",
        "Add a getting-started page for new devs",
        "Keep external links steady while icons load",
        "`uv.lock` stays in sync with the pyprojects",
        "Release ghga/15.3.1",
    ],
)
def test_titles_in_the_grammar_pass(title):
    """A stack, a key and a code span at the start are all optional and allowed."""
    assert title_problems(title) == []


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("chore: publish dev charts to GHCR", ["label", "capital"]),
        ("feat(ucs)!: Add the endpoints", ["label"]),
        (
            "Box version: Hexkit - Add precondition for DAO.update() (GSI-2639)",
            ["label"],
        ),
        (
            "Box version: (GSI-2664) - Replace `mapping` with `filter_`",
            ["key", "label"],
        ),
        ("Add UCS endpoints (GSI-1234).", ["full stop"]),
        ("GSI-1234 Add UCS endpoints", ["key"]),
        ("[Upload] Add UCS endpoints", ["square brackets"]),
        ("[upload]Add UCS endpoints", ["square brackets"]),
        ("add UCS endpoints", ["capital"]),
        ("(GSI-1234)", ["description"]),
    ],
)
def test_titles_outside_the_grammar_name_each_problem(title, expected):
    """Each problem is reported once, and nothing the title gets right is reported."""
    problems = title_problems(title)
    assert len(problems) == len(expected), problems
    for problem, word in zip(problems, expected, strict=True):
        assert word in problem


@pytest.mark.parametrize(
    ("head", "base", "exempt"),
    [
        ("renovate/chainguard-minio-images", "dev", True),
        ("automated/security-scan", "dev", True),
        ("dev", "main", True),
        ("hotfix/fix-login", "main", True),
        ("docs/style-rules", "dev", False),
        (
            "GSI-2540-pr-skills/docs/add-ghga-review",
            "GSI-2540-pr-skills/chore/x",
            False,
        ),
    ],
)
def test_releases_hotfixes_and_bots_are_exempt(head, base, exempt):
    """A stacked PR targets the branch below it, not `dev`, and is still checked."""
    assert is_exempt(head, base) is exempt


def _run(title, tmp_path, head="docs/x", base="dev"):
    summary = tmp_path / "summary.md"
    env = {"GITHUB_ACTIONS": "true", "GITHUB_STEP_SUMMARY": str(summary)}
    result = subprocess.run(
        [sys.executable, CHECK, "--head", head, "--base", base, "--", title],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return result, summary


def test_a_bad_title_warns_without_failing(tmp_path):
    """The check only warns: annotations and a summary, and exit status 0."""
    result, summary = _run("chore: publish dev charts", tmp_path)
    assert result.returncode == 0
    assert "::warning title=PR title::No label" in result.stdout
    assert "[upload] Add UCS endpoints (GSI-1234)" in result.stdout
    assert "chore: publish dev charts" in summary.read_text()


def test_a_good_or_exempt_title_writes_no_warning(tmp_path):
    """Neither a title in the grammar nor an exempt PR leaves a summary behind."""
    for title, base in [("Add UCS endpoints", "dev"), ("chore: bump", "main")]:
        result, summary = _run(title, tmp_path, base=base)
        assert result.returncode == 0
        assert "::warning" not in result.stdout
        assert not summary.exists()
