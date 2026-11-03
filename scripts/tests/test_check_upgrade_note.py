"""Tests for check_upgrade_note.py: which descriptions pass, and what the notes read."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from check_upgrade_note import is_exempt, main, upgrade_lines, upgrade_notes

TEMPLATE_HINT = (
    "<!--\nEnd with one line per action an upgrade requires:\nUpgrade: none\n-->"
)


@pytest.mark.parametrize(
    ("head", "base", "exempt"),
    [
        ("renovate/minio-images", "dev", True),
        ("automated/security-scan", "dev", True),
        ("dev", "main", True),
        ("main", "dev", True),
        ("hotfix/crash", "main", False),
        ("feat/GSI-1-add-x", "dev", False),
        ("upload/feat/add-y", "upload/feat/add-x", False),
    ],
)
def test_exempt_pull_requests(head, base, exempt):
    """A hotfix can need an upgrade note as much as a feature does."""
    assert is_exempt(head, base) is exempt


def test_lines_are_read_folded_and_counted_with_none():
    body = (
        "Renames the flag.\r\n\r\n"
        "Upgrade: rename `--db` to `--db-name`\r\n"
        "Upgrade: set `config.db_name` from\r\n"
        "  `mongodb.dbName` instead\r\n"
        "Upgrade: none\r\n"
    )
    assert upgrade_lines(body) == [
        "rename `--db` to `--db-name`",
        "set `config.db_name` from `mongodb.dbName` instead",
        "none",
    ]


@pytest.mark.parametrize("none", ["none", "None", "NONE.", "none   "])
def test_none_is_no_note(none):
    assert upgrade_notes(f"Upgrade: {none}\nUpgrade: drop `x`") == ["drop `x`"]


@pytest.mark.parametrize(
    "body",
    [
        "",
        TEMPLATE_HINT,
        "- Upgrade: inside a bullet",
        "Upgrade:",
        "Upgrade:   \nnext paragraph",
        "upgrade: lower case",
    ],
)
def test_no_upgrade_line(body):
    """The template's example sits in a comment and must not count as an answer."""
    assert upgrade_lines(body) == []


def test_check_passes_with_none_and_fails_without_a_line(capsys, monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    assert main(["--head", "feat/x", "--base", "dev", "--", "Upgrade: none"]) == 0
    assert main(["--head", "feat/x", "--base", "dev", "--", TEMPLATE_HINT]) == 1
    assert "`Upgrade: none`" in capsys.readouterr().out


def test_check_annotates_and_summarises_in_actions(tmp_path, capsys, monkeypatch):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert main(["--head", "feat/x", "--base", "dev", "--", "No line"]) == 1
    assert capsys.readouterr().out.startswith("::error title=Upgrade note::")
    assert "Missing upgrade note" in summary.read_text()


def test_exempt_pull_request_passes_without_a_line():
    assert main(["--head", "dev", "--base", "main", "--", ""]) == 0
