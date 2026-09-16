"""Tests for adr_check.py: the per-file rules, supersession, references and the index."""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import adr_check

BODY = """
## Summary

In the context of **x**

## Details

### Context

### Decision

### Consequences

### Alternatives
"""


def _adr(number: str, title: str = "A decision", fields: str = "", body: str = BODY):
    meta = fields or "status: accepted\ndate: 2026-09-15\ntags: [docs]\n"
    return f"---\n{meta}---\n\n# ADR-{number} — {title}\n{body}"


@pytest.fixture
def repo(tmp_path):
    """A git repo with two valid ADRs, a template and an empty index."""
    adrs = tmp_path / "docs/adrs"
    adrs.mkdir(parents=True)
    (adrs / "adr-template.md").write_text("# ADR-NNNN — {Title}\n" + BODY)
    (adrs / "adr-0001-first.md").write_text(_adr("0001", "First"))
    (adrs / "adr-0002-second.md").write_text(_adr("0002", "Second"))
    (tmp_path / "docs/README.md").write_text(
        "# Docs\n\n<!-- adr-index:start -->\n<!-- adr-index:end -->\n\nMore.\n"
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    return tmp_path


def _run(repo: Path, capsys, *argv: str) -> tuple[int, str]:
    code = adr_check.main(list(argv), root=repo)
    return code, capsys.readouterr().err


def _stage(repo: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)


def test_valid_set_regenerates_index_once(repo, capsys):
    """The first run writes the index and fails; the second finds nothing to do."""
    _stage(repo)
    code, out = _run(repo, capsys)
    assert code == 1
    assert "regenerated the ADR index" in out
    readme = (repo / "docs/README.md").read_text()
    assert "| [0001](adrs/adr-0001-first.md) | First | accepted | docs |" in readme
    assert "0000" not in readme
    assert readme.endswith("<!-- adr-index:end -->\n\nMore.\n")
    assert _run(repo, capsys) == (0, "")


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ("status: accepted\ndate: 2026-09-15\n", "missing field 'tags'"),
        ("status: done\ndate: 2026-09-15\ntags: [docs]\n", "status 'done'"),
        ("status: accepted\ndate: 15.09.2026\ntags: [docs]\n", "date must be"),
        ("status: accepted\ndate: 2026-09-15\ntags: [ci]\n", "unknown tag 'ci'"),
        ("status: accepted\ndate: 2026-09-15\ntags: []\n", "tags must be"),
        ("status: accepted\ndate: 2026-09-15\ntags: [docs]\nid: 1\n", "unknown field"),
        (
            "status: accepted\ndate: 2026-09-15\ntags: [docs]\nrelated: [ADR-0009]\n",
            "related names ADR-0009",
        ),
        (
            "status: accepted\ndate: 2026-09-15\ntags: [docs]\nrelated: [ADR-0001]\n",
            "names the ADR itself",
        ),
    ],
)
def test_frontmatter_rules(repo, fields, expected):
    (repo / "docs/adrs/adr-0001-first.md").write_text(_adr("0001", "First", fields))
    _, problems = adr_check.load_adrs(repo)
    assert any(expected in p for p in problems), problems


def test_file_name_title_and_duplicates(repo):
    adrs = repo / "docs/adrs"
    (adrs / "0003_bad.md").write_text(_adr("0003"))
    (adrs / "adr-0002-again.md").write_text(_adr("0002"))
    (adrs / "adr-0004-wrong-number.md").write_text(_adr("0005"))
    _, problems = adr_check.load_adrs(repo)
    assert any("0003_bad.md: file name" in p for p in problems)
    assert any("number 0002 is taken" in p for p in problems)
    assert any("adr-0004-wrong-number.md: first line" in p for p in problems)


def test_headings_out_of_order_and_extra_level_two(repo):
    swapped = BODY.replace("### Context", "### X").replace(
        "### Decision", "### Context"
    )
    (repo / "docs/adrs/adr-0001-first.md").write_text(_adr("0001", body=swapped))
    extra = BODY + "\n### Further\n\n## Appendix\n"
    (repo / "docs/adrs/adr-0002-second.md").write_text(_adr("0002", body=extra))
    _, problems = adr_check.load_adrs(repo)
    assert any(p.startswith("adr-0001-first.md: headings") for p in problems)
    assert any("'## Appendix'" in p for p in problems)
    assert not any("Further" in p for p in problems)


def test_supersession_must_be_symmetric(repo):
    superseded = "status: superseded\ndate: 2026-09-15\ntags: [docs]\n"
    (repo / "docs/adrs/adr-0001-first.md").write_text(
        _adr("0001", fields=superseded + "superseded-by: [ADR-0002]\n")
    )
    _, problems = adr_check.load_adrs(repo)
    assert problems == [
        "adr-0001-first.md: superseded by ADR-0002, which lacks supersedes: [ADR-0001]"
    ]
    (repo / "docs/adrs/adr-0002-second.md").write_text(
        _adr(
            "0002",
            fields="status: accepted\ndate: 2026-09-15\ntags: [docs]\n"
            "supersedes: [ADR-0001]\n",
        )
    )
    assert adr_check.load_adrs(repo)[1] == []


def test_superseded_status_needs_superseded_by(repo):
    (repo / "docs/adrs/adr-0001-first.md").write_text(
        _adr("0001", fields="status: superseded\ndate: 2026-09-15\ntags: [docs]\n")
    )
    assert adr_check.load_adrs(repo)[1] == [
        "adr-0001-first.md: status superseded needs superseded-by"
    ]


def test_references(repo, capsys):
    (repo / "notes.md").write_text(
        "ADR-0001 and ADR-0001/0002 and ADR-0001\u20130002 are fine.\n"
        "ADR-0003 is gone, so is ADR-0001/0007, and ADR-0001/12 is ambiguous.\n"
        "[ok](docs/adrs/adr-0002-second.md) [gone](../adrs/adr-0002-renamed.md)\n"
    )
    (repo / "docs/adrs/adr-0002-second.md").write_text(
        _adr(
            "0002",
            body=BODY + "\nSee [first](adr-0001-first.md), [x](adr-0001-old.md).\n",
        )
    )
    code, out = _run(
        repo, capsys, "--refs", "notes.md", "docs/adrs/adr-0002-second.md", "gone.md"
    )
    assert code == 1
    lines = out.splitlines()
    assert lines[:4] == [
        "notes.md:2: ADR-0003 does not exist",
        "notes.md:2: ADR-0007 does not exist",
        "notes.md:2: 'ADR-0001/12' needs four-digit numbers",
        "notes.md:3: link to docs/adrs/adr-0002-renamed.md, which does not exist",
    ]
    assert len(lines) == 5
    assert lines[4].startswith("docs/adrs/adr-0002-second.md:")
    assert lines[4].endswith("link to docs/adrs/adr-0001-old.md, which does not exist")


def test_set_check_scans_tracked_files(repo, capsys):
    (repo / "tracked.txt").write_text("ADR-0042\n")
    (repo / "untracked.txt").write_text("ADR-0043\n")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    _, out = _run(repo, capsys)
    assert "tracked.txt:1: ADR-0042 does not exist" in out
    assert "ADR-0043" not in out


def test_missing_index_markers(repo, capsys):
    (repo / "docs/README.md").write_text("# Docs\n")
    _, out = _run(repo, capsys)
    assert "missing <!-- adr-index:start -->" in out
