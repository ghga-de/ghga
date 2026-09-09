"""Tests for affected_targets.py, focused on what it does when the base ref is missing.

The default base is `origin/dev` (ADR-0020), a remote-tracking ref that a clone which has
not fetched since `dev` was created simply does not have. Answering that from the working
tree would report "nothing affected" for a branch whose work is committed — the tree is
clean, so the fallback saw an empty change set it had never looked at.
"""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "affected_targets.py"

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


def test_resolvable_base_still_reports_targets():
    """The happy path is unchanged: a real base ref produces a normal verdict."""
    result = _run("--base", "HEAD")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload == {"all": False, "targets": []}
