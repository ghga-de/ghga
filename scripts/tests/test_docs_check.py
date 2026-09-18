"""Tests for docs_check.py: the ADR rules, the epic shape, references and the indexes."""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import docs_check

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


def _epic(title: str, code_name: str, kind: str = "Implementation Epic"):
    return f"# {title} ({code_name})\n**Epic Type:** {kind}\n"


@pytest.fixture
def repo(tmp_path):
    """A git repo with two valid ADRs, two valid epics, and empty indexes."""
    adrs = tmp_path / "docs/adrs"
    adrs.mkdir(parents=True)
    (adrs / "adr-template.md").write_text("# ADR-NNNN — {Title}\n" + BODY)
    (adrs / "adr-0001-first.md").write_text(_adr("0001", "First"))
    (adrs / "adr-0002-second.md").write_text(_adr("0002", "Second"))
    (tmp_path / "docs/README.md").write_text(
        "# Docs\n\n<!-- adr-index:start -->\n<!-- adr-index:end -->\n\nMore.\n"
    )
    epics = tmp_path / "docs/epics"
    epics.mkdir()
    (epics / "epic-0001-blob-fish.md").write_text(_epic("Catalog", "Blob Fish"))
    (epics / "epic-0002-wood-ant").mkdir()
    (epics / "epic-0002-wood-ant/README.md").write_text(
        _epic("Identity", "Wood Ant", "Exploratory Epic")
    )
    (epics / "epic-0002-wood-ant/images").mkdir()
    (epics / "epic-0002-wood-ant/images/j.png").write_bytes(b"x")
    (epics / "README.md").write_text(
        "# Epics\n\n<!-- epic-index:start -->\n<!-- epic-index:end -->\n"
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    return tmp_path


def _run(repo: Path, capsys, *argv: str) -> tuple[int, str]:
    code = docs_check.main(list(argv), root=repo)
    return code, capsys.readouterr().err


def _stage(repo: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)


def test_valid_set_regenerates_indexes_once(repo, capsys):
    """The first run writes both indexes and fails; the second finds nothing to do."""
    _stage(repo)
    code, out = _run(repo, capsys)
    assert code == 1
    assert out.splitlines() == [
        "docs/README.md: regenerated the index; stage the file",
        "docs/epics/README.md: regenerated the index; stage the file",
    ]
    readme = (repo / "docs/README.md").read_text()
    assert "| [0001](adrs/adr-0001-first.md) | First | accepted | docs |" in readme
    assert "0000" not in readme
    assert readme.endswith("<!-- adr-index:end -->\n\nMore.\n")
    epics = (repo / "docs/epics/README.md").read_text()
    assert "1. [Blob Fish](./epic-0001-blob-fish.md): Catalog\n" in epics
    assert "2. [Wood Ant](./epic-0002-wood-ant/README.md): Identity\n" in epics
    assert _run(repo, capsys) == (0, "")


def test_epic_index_numbers_gaps(repo, capsys):
    """A gap in the numbering switches the index from an ordered to a bullet list."""
    epics = repo / "docs/epics"
    (epics / "epic-0004-giraffe.md").write_text(_epic("Lifecycle", "Giraffe"))
    _stage(repo)
    _run(repo, capsys)
    lines = (epics / "README.md").read_text()
    assert "- (1) [Blob Fish](./epic-0001-blob-fish.md): Catalog\n" in lines
    assert "- (4) [Giraffe](./epic-0004-giraffe.md): Lifecycle\n" in lines


def test_epic_index_keeps_the_heading_casing(repo, capsys):
    """The code name is taken from the heading as written, not title-cased."""
    epics = repo / "docs/epics"
    (epics / "epic-0003-mermaids-purse.md").write_text(_epic("IDs", "Mermaid's Purse"))
    (epics / "epic-0004-red-billed-quelea.md").write_text(
        _epic("Batch", "Red-billed Quelea")
    )
    _stage(repo)
    _run(repo, capsys)
    index = (epics / "README.md").read_text()
    assert "3. [Mermaid's Purse](./epic-0003-mermaids-purse.md): IDs\n" in index
    assert "4. [Red-billed Quelea](./epic-0004-red-billed-quelea.md): Batch\n" in index


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("epic-12-short.md", "name is not epic-NNNN-kebab-case"),
        ("epic-0003-Bad_Name.md", "name is not epic-NNNN-kebab-case"),
        ("epic-0001-blob-fish.md", "number 0001 is taken"),
    ],
)
def test_epic_names(repo, name, expected):
    (repo / "docs/epics" / name.replace("0001-blob-fish", "0001-other")).write_text(
        _epic("X", "Y")
    )
    problems = docs_check.load_epics(repo)[1]
    assert any(expected in p for p in problems), problems


def test_epic_shape_must_earn_its_directory(repo):
    """A directory with nothing but the spec should be a single file instead."""
    epics = repo / "docs/epics"
    (epics / "epic-0003-axolotl").mkdir()
    (epics / "epic-0003-axolotl/README.md").write_text(_epic("Mocking", "Axolotl"))
    (epics / "epic-0005-nautilus").mkdir()
    (epics / "epic-0005-nautilus/notes.md").write_text("no spec here\n")
    problems = docs_check.load_epics(repo)[1]
    assert "epic-0003-axolotl: is a directory with nothing but README.md" in " ".join(
        problems
    )
    assert any(
        "epic-0005-nautilus: is a directory without README.md" in p for p in problems
    )


def test_epic_file_and_directory_collide(repo):
    (repo / "docs/epics/epic-0001-blob-fish").mkdir()
    (repo / "docs/epics/epic-0001-blob-fish/README.md").write_text(
        _epic("C", "Blob Fish")
    )
    problems = docs_check.load_epics(repo)[1]
    assert problems == ["epic-0001-blob-fish: exists as a file and as a directory"]


def test_epic_title_must_name_the_code_name(repo):
    (repo / "docs/epics/epic-0001-blob-fish.md").write_text(
        "# Catalog\n**Epic Type:** Implementation Epic\n"
    )
    problems = docs_check.load_epics(repo)[1]
    assert problems == [
        "epic-0001-blob-fish: first heading must be '# Description (Code Name)'"
    ]


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("", "no '**Epic Type:** ...' line"),
        (
            "**Epic Type:** Half Exploration",
            "epic type 'Half Exploration' is not one of",
        ),
        ("**Epic Type:** implementation epic", "is not one of"),
    ],
)
def test_epic_type(repo, line, expected):
    (repo / "docs/epics/epic-0001-blob-fish.md").write_text(
        f"# Catalog (Blob Fish)\n{line}\n"
    )
    problems = docs_check.load_epics(repo)[1]
    assert any(expected in p for p in problems), problems


def test_epic_type_allows_the_mixed_kind(repo):
    (repo / "docs/epics/epic-0001-blob-fish.md").write_text(
        _epic("Catalog", "Blob Fish", "Exploration and Implementation Epic")
    )
    assert docs_check.load_epics(repo)[1] == []


def test_epic_links(repo, capsys):
    (repo / "notes.md").write_text(
        "[ok](docs/epics/epic-0001-blob-fish.md) [gone](docs/epics/epic-0009-gone.md)\n"
    )
    (repo / "docs/epics/epic-0001-blob-fish.md").write_text(
        _epic("Catalog", "Blob Fish")
        + "\n[ok](./epic-0002-wood-ant/README.md) [x](./epic-0009-gone.md)\n"
    )
    code, out = _run(
        repo, capsys, "--refs", "notes.md", "docs/epics/epic-0001-blob-fish.md"
    )
    assert code == 1
    assert out.splitlines() == [
        "notes.md:1: link to docs/epics/epic-0009-gone.md, which does not exist",
        "docs/epics/epic-0001-blob-fish.md:4: link to "
        "docs/epics/epic-0009-gone.md, which does not exist",
    ]


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
    _, problems = docs_check.load_adrs(repo)
    assert any(expected in p for p in problems), problems


def test_file_name_title_and_duplicates(repo):
    adrs = repo / "docs/adrs"
    (adrs / "0003_bad.md").write_text(_adr("0003"))
    (adrs / "adr-0002-again.md").write_text(_adr("0002"))
    (adrs / "adr-0004-wrong-number.md").write_text(_adr("0005"))
    _, problems = docs_check.load_adrs(repo)
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
    _, problems = docs_check.load_adrs(repo)
    assert any(p.startswith("adr-0001-first.md: headings") for p in problems)
    assert any("'## Appendix'" in p for p in problems)
    assert not any("Further" in p for p in problems)


def test_supersession_must_be_symmetric(repo):
    superseded = "status: superseded\ndate: 2026-09-15\ntags: [docs]\n"
    (repo / "docs/adrs/adr-0001-first.md").write_text(
        _adr("0001", fields=superseded + "superseded-by: [ADR-0002]\n")
    )
    _, problems = docs_check.load_adrs(repo)
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
    assert docs_check.load_adrs(repo)[1] == []


def test_superseded_status_needs_superseded_by(repo):
    (repo / "docs/adrs/adr-0001-first.md").write_text(
        _adr("0001", fields="status: superseded\ndate: 2026-09-15\ntags: [docs]\n")
    )
    assert docs_check.load_adrs(repo)[1] == [
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


STUB = "@AGENTS.md\n\n# Claude Code instructions\n\n`AGENTS.md` holds the rules.\n"
COPILOT = "# GitHub Copilot instructions\n\n`AGENTS.md` holds the rules.\n"


@pytest.fixture
def agents(repo):
    """The `repo` fixture with a conforming set of instruction files on top."""
    (repo / "AGENTS.md").write_text("# Agent Instructions\n")
    (repo / "CLAUDE.md").write_text(STUB)
    (repo / ".github").mkdir()
    (repo / ".github/copilot-instructions.md").write_text(COPILOT)
    (repo / "libs").mkdir()
    (repo / "libs/AGENTS.md").write_text("# Agent Instructions for libs\n")
    (repo / "libs/CLAUDE.md").write_text(STUB)
    (repo / "libs/.agents/skills/qa").mkdir(parents=True)
    (repo / "libs/.agents/skills/qa/SKILL.md").write_text("---\nname: qa\n---\n")
    return repo


def _instruction_problems(repo: Path) -> list[str]:
    _stage(repo)
    return docs_check.check_instruction_files(repo)


def test_conforming_instruction_files(agents):
    """A complete set of area files, stubs and skills reports nothing."""
    assert _instruction_problems(agents) == []


def test_agents_file_needs_its_stub(agents):
    """Claude Code finds a nested area file only through the CLAUDE.md beside it."""
    (agents / "libs/CLAUDE.md").unlink()
    assert _instruction_problems(agents) == [
        "libs/AGENTS.md: no CLAUDE.md stub beside it"
    ]


def test_stub_needs_its_agents_file(agents):
    """A stub pointing at nothing is a dangling import."""
    (agents / "services").mkdir()
    (agents / "services/CLAUDE.md").write_text(STUB)
    assert "services/CLAUDE.md: no AGENTS.md beside it" in _instruction_problems(agents)


def test_missing_copilot_stub(agents):
    """The root set owes Copilot its one pointer."""
    (agents / ".github/copilot-instructions.md").unlink()
    problems = _instruction_problems(agents)
    assert problems == [
        ".github/copilot-instructions.md: missing; Copilot has no pointer to AGENTS.md"
    ]


@pytest.mark.parametrize(
    "stub,expected",
    [
        ("", "the stub is empty"),
        ("# Claude\n\nSee AGENTS.md.\n", "the first line must be"),
        (STUB + "\n## More\n\nRules.\n", "carries one heading, not 2"),
        (STUB + "\n- Prefer minimal diffs\n", "carries no content of its own"),
        (STUB + "\n@docs/style.md\n", "carries no content of its own"),
        (STUB + "\nOne.\nTwo.\nThree.\nFour.\n", "the stub is 7 lines"),
    ],
)
def test_stub_carries_nothing_of_its_own(agents, stub, expected):
    """Anything beyond the import, a heading and a sentence belongs in the AGENTS.md."""
    (agents / "libs/CLAUDE.md").write_text(stub)
    problems = _instruction_problems(agents)
    assert any(expected in p for p in problems), problems


def test_orphan_instruction_paths(agents):
    """An instruction file no tool reads is worse than none: it looks maintained."""
    (agents / "docs/epics/.copilot").mkdir()
    (agents / "docs/epics/.copilot/instructions.md").write_text("Write epics.\n")
    (agents / ".cursorrules").write_text("Be brief.\n")
    assert _instruction_problems(agents) == [
        ".cursorrules: an instruction file at a path no tool reads",
        "docs/epics/.copilot/instructions.md: an instruction file at a path no tool reads",
    ]


def test_skill_outside_the_standard_path(agents):
    """Only `.agents/skills/` is read by every tool, so that is where a skill lives."""
    (agents / "libs/.claude/skills/qa").mkdir(parents=True)
    (agents / "libs/.claude/skills/qa/SKILL.md").write_text("---\nname: qa\n---\n")
    assert _instruction_problems(agents) == [
        "libs/.claude/skills/qa/SKILL.md: a skill belongs under .agents/skills/<name>/"
    ]


def test_a_dotted_area_keeps_its_leading_dot(agents):
    """`.github/AGENTS.md` is reported at its real path, not as `github/AGENTS.md`."""
    (agents / ".github/AGENTS.md").write_text("# Agent Instructions for .github\n")
    assert _instruction_problems(agents) == [
        ".github/AGENTS.md: no CLAUDE.md stub beside it"
    ]


def test_a_tracked_stub_missing_from_the_tree_is_skipped(agents):
    """A half-applied rebase must not bury every other problem under a traceback."""
    (agents / "services").mkdir()
    (agents / "services/CLAUDE.md").write_text(STUB)
    _stage(agents)
    (agents / "libs/CLAUDE.md").unlink()
    assert docs_check.check_instruction_files(agents) == [
        "services/CLAUDE.md: no AGENTS.md beside it"
    ]
