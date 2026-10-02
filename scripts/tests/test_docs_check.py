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


def _epic_index(completed: str = "", unfolding: str = "") -> str:
    return (
        "# Epics\n\n## Completed\n\n"
        f"<!-- epic-index:completed:start -->\n{completed}"
        "<!-- epic-index:completed:end -->\n\n## Unfolding\n\n"
        f"<!-- epic-index:unfolding:start -->\n{unfolding}"
        "<!-- epic-index:unfolding:end -->\n"
    )


def _epic_lists(repo: Path) -> tuple[str, str]:
    """Return the completed and the unfolding list from the epic index."""
    text = (repo / "docs/epics/README.md").read_text()
    lists = []
    for marks in (docs_check.EPIC_COMPLETED_MARKS, docs_check.EPIC_UNFOLDING_MARKS):
        start, end = (text.index(mark) for mark in marks)
        lists.append(text[start + len(marks[0]) + 1 : end])
    return lists[0], lists[1]


@pytest.fixture
def repo(tmp_path):
    """A git repo with two valid ADRs, two valid epics, no skills, and empty indexes."""
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
    (epics / "README.md").write_text(_epic_index())
    (tmp_path / "docs/agent-skills.md").write_text(
        "# Skills\n\n<!-- skill-index:start -->\nNone at the moment.\n"
        "<!-- skill-index:end -->\n"
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
    assert _epic_lists(repo) == (
        "None at the moment.\n",
        "1. [Blob Fish](./epic-0001-blob-fish.md): Catalog\n"
        "2. [Wood Ant](./epic-0002-wood-ant/README.md): Identity\n",
    )
    assert _run(repo, capsys) == (0, "")


def test_moved_epic_stays_completed(repo, capsys):
    """A line moved into the completed list stays there and is regenerated."""
    (repo / "docs/epics/README.md").write_text(
        _epic_index(completed="- [stale](./epic-0001-blob-fish.md): old title\n")
    )
    _stage(repo)
    _run(repo, capsys)
    assert _epic_lists(repo) == (
        "1. [Blob Fish](./epic-0001-blob-fish.md): Catalog\n",
        "2. [Wood Ant](./epic-0002-wood-ant/README.md): Identity\n",
    )
    assert _run(repo, capsys) == (0, "")


def test_epic_in_both_lists_counts_as_completed(repo, capsys):
    """A line copied rather than moved leaves the epic in the completed list only."""
    line = "1. [Blob Fish](./epic-0001-blob-fish.md): Catalog\n"
    (repo / "docs/epics/README.md").write_text(_epic_index(line, line))
    _stage(repo)
    _run(repo, capsys)
    assert _epic_lists(repo) == (
        line,
        "2. [Wood Ant](./epic-0002-wood-ant/README.md): Identity\n",
    )


def test_epic_lists_share_the_style(repo, capsys):
    """A gap in one list makes both lists bullet lists."""
    epics = repo / "docs/epics"
    (epics / "epic-0003-giraffe.md").write_text(_epic("Lifecycle", "Giraffe"))
    (epics / "README.md").write_text(
        _epic_index(
            completed="- (1) [x](./epic-0001-x.md)\n- (3) [y](./epic-0003-y.md)\n"
        )
    )
    _stage(repo)
    _run(repo, capsys)
    assert _epic_lists(repo) == (
        "- (1) [Blob Fish](./epic-0001-blob-fish.md): Catalog\n"
        "- (3) [Giraffe](./epic-0003-giraffe.md): Lifecycle\n",
        "- (2) [Wood Ant](./epic-0002-wood-ant/README.md): Identity\n",
    )


def test_epic_index_needs_both_lists(repo, capsys):
    (repo / "docs/epics/README.md").write_text(
        "# Epics\n\n<!-- epic-index:completed:start -->\n"
        "<!-- epic-index:completed:end -->\n"
    )
    _stage(repo)
    code, out = _run(repo, capsys)
    assert code == 1
    assert (
        "docs/epics/README.md: missing <!-- epic-index:unfolding:start -->"
        " or <!-- epic-index:unfolding:end -->"
    ) in out.splitlines()


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


COPILOT = "# GitHub Copilot instructions\n\n`AGENTS.md` holds the rules.\n"


@pytest.fixture
def agents(repo):
    """The `repo` fixture with a conforming set of instruction files on top."""
    (repo / "AGENTS.md").write_text("# Agent Instructions\n")
    (repo / ".github").mkdir()
    (repo / ".github/copilot-instructions.md").write_text(COPILOT)
    (repo / "libs").mkdir()
    (repo / "libs/AGENTS.md").write_text("# Agent Instructions for libs\n")
    _skill(repo, "libs", "qa")
    return repo


def _skill(
    repo: Path, base: str, name: str, fields: str = "", body: str = "# Skill\n"
) -> Path:
    """Write a skill and its Claude Code symlink; return the SKILL.md."""
    prefix = repo / base if base else repo
    meta = fields or f"name: {name}\ndescription: Do {name}.\n"
    path = prefix / ".agents/skills" / name / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text(f"---\n{meta}---\n\n{body}")
    (prefix / ".claude/skills").mkdir(parents=True, exist_ok=True)
    (prefix / ".claude/skills" / name).symlink_to(f"../../.agents/skills/{name}")
    return path


def _instruction_problems(repo: Path) -> list[str]:
    _stage(repo)
    return docs_check.check_instruction_files(repo)


def test_conforming_instruction_files(agents):
    """A complete set of area files, the Copilot stub and skills reports nothing."""
    assert _instruction_problems(agents) == []


@pytest.mark.parametrize(
    "rel", ["CLAUDE.md", "libs/CLAUDE.md", ".claude/CLAUDE.md", "libs/CLAUDE.local.md"]
)
def test_no_committed_claude_file(agents, rel):
    """One CLAUDE.md in or above the working directory switches AGENTS.md off."""
    (agents / rel).parent.mkdir(exist_ok=True)
    (agents / rel).write_text("@AGENTS.md\n")
    assert _instruction_problems(agents) == [
        f"{rel}: a committed CLAUDE.md stops Claude Code reading AGENTS.md;"
        " move its rules into the AGENTS.md"
    ]


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
        ("# Copilot\n\nSee the docs.\n", "the stub must point at AGENTS.md"),
        (COPILOT + "\n## More\n\nRules.\n", "carries one heading, not 2"),
        (COPILOT + "\n- Prefer minimal diffs\n", "carries no content of its own"),
        (COPILOT + "\n@docs/style.md\n", "carries no content of its own"),
        (COPILOT + "\nOne.\nTwo.\nThree.\nFour.\nFive.\n", "the stub is 7 lines"),
    ],
)
def test_stub_carries_nothing_of_its_own(agents, stub, expected):
    """Anything beyond a heading and a sentence belongs in the AGENTS.md."""
    (agents / ".github/copilot-instructions.md").write_text(stub)
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
    (agents / "libs/.claude/skills/lint").mkdir(parents=True)
    (agents / "libs/.claude/skills/lint/SKILL.md").write_text("---\nname: lint\n---\n")
    assert _instruction_problems(agents) == [
        "libs/.claude/skills/lint/SKILL.md: a skill belongs under .agents/skills/<name>/"
    ]


def test_a_tracked_stub_missing_from_the_tree_is_skipped(agents):
    """A half-applied rebase must not bury every other problem under a traceback."""
    _stage(agents)
    (agents / ".github/copilot-instructions.md").unlink()
    assert docs_check.check_instruction_files(agents) == []


def _skill_problems(repo: Path) -> tuple[list[str], list[str]]:
    """Return the problems and the warnings of the skill checks."""
    _stage(repo)
    tracked = docs_check._tracked(repo)
    _, problems, warnings = docs_check.load_skills(repo, tracked)
    return problems + docs_check.check_skill_links(repo, tracked), warnings


def test_conforming_skills(agents):
    """A skill with name, description and its symlink reports nothing."""
    _skill(agents, "", "adr", "name: adr\ndescription: Write an ADR.\npaths: [a/**]\n")
    assert _skill_problems(agents) == ([], [])


@pytest.mark.parametrize(
    "name,fields,expected",
    [
        ("adr", "description: x\n", "name None must equal its directory 'adr'"),
        ("adr", "name: ADR\ndescription: x\n", "name 'ADR' must equal its directory"),
        ("a--b", "name: a--b\ndescription: x\n", "lowercase letters, digits"),
        ("a" * 65, f"name: {'a' * 65}\ndescription: x\n", "1 to 64 lowercase"),
        ("adr", "name: adr\n", "missing description"),
        ("adr", "name: adr\ndescription: ''\n", "missing description"),
        ("adr", f"name: adr\ndescription: {'x' * 1025}\n", "1025 characters; at most"),
        ("adr", "name: adr\ndescription: x\nmodel: haiku\n", "unknown field 'model'"),
        (
            "adr",
            "name: adr\ndescription: x\ndisable-model-invocation: yes please\n",
            "disable-model-invocation must be true or false",
        ),
        ("adr", "name: adr\ndescription: x\npaths: 3\n", "paths must be a glob"),
        ("adr", "name: [adr\n", "frontmatter must be a YAML mapping"),
    ],
)
def test_skill_frontmatter(agents, name, fields, expected):
    _skill(agents, "", name, fields)
    problems, _ = _skill_problems(agents)
    assert any(expected in p for p in problems), problems


def test_skill_without_frontmatter(agents):
    path = _skill(agents, "", "adr")
    path.write_text("# ADR\n")
    problems, _ = _skill_problems(agents)
    assert problems == [
        ".agents/skills/adr/SKILL.md: frontmatter must be a YAML mapping between ---"
    ]


def test_long_description_warns(agents, capsys):
    """Past 300 characters a description crowds the listing, but still loads."""
    _skill(agents, "", "adr", f"name: adr\ndescription: {'x' * 301}\n")
    problems, warnings = _skill_problems(agents)
    assert problems == []
    assert warnings == [
        ".agents/skills/adr/SKILL.md: description is 301 characters; keep it under 300"
    ]
    _run(agents, capsys)  # regenerate the indexes
    _stage(agents)
    code, out = _run(agents, capsys)
    assert code == 0
    assert out == f"warning: {warnings[0]}\n"


def test_skill_links(agents):
    """Relative links resolve from the SKILL.md; URLs, anchors and code are skipped."""
    body = (
        "[style](../../../docs/README.md#adrs) [gone](../../../docs/gone.md)\n"
        "[web](https://example.org) [here](#steps) <x@example.org>\n"
        "```md\n[example](nowhere.md)\n```\n"
    )
    _skill(agents, "", "adr", body=body)
    problems, _ = _skill_problems(agents)
    assert problems == [
        ".agents/skills/adr/SKILL.md: link to ../../../docs/gone.md, which does not exist"
    ]


def test_skill_symlink(agents):
    """Each skill has a relative symlink beside its .agents/, and each link a skill."""
    _skill(agents, "", "adr")
    _skill(agents, "", "epic")
    (agents / ".claude/skills/adr").unlink()
    (agents / ".claude/skills/epic").unlink()
    (agents / ".claude/skills/epic").symlink_to(agents / ".agents/skills/epic")
    (agents / ".claude/skills/gone").symlink_to("../../.agents/skills/gone")
    problems, _ = _skill_problems(agents)
    assert problems == [
        ".claude/skills/adr: missing; link it to ../../.agents/skills/adr",
        ".claude/skills/epic: must be a symlink to ../../.agents/skills/epic",
        ".claude/skills/gone: no skill at .agents/skills/gone",
    ]


def test_skill_symlink_must_not_be_a_copy(agents):
    _skill(agents, "", "adr")
    (agents / ".claude/skills/adr").unlink()
    (agents / ".claude/skills/adr").write_text("../../.agents/skills/adr")
    problems, _ = _skill_problems(agents)
    assert problems == [
        ".claude/skills/adr: must be a symlink to ../../.agents/skills/adr"
    ]


def _budgets(repo: Path) -> dict[str, tuple[int, int]]:
    _stage(repo)
    tracked = docs_check._tracked(repo)
    skills, _, _ = docs_check.load_skills(repo, tracked)
    return {
        b.area: (b.total, b.descriptions)
        for b in docs_check.context_budget(repo, tracked, skills)
    }


def test_context_budget(agents):
    """Each session counts the AGENTS.md chain, the output style, visible descriptions."""
    (agents / "AGENTS.md").write_text("a" * 400)  # 100 tokens
    (agents / "libs/AGENTS.md").write_text("b" * 800)  # 200 tokens
    (agents / ".claude/output-styles").mkdir(parents=True)
    (agents / docs_check.OUTPUT_STYLE).write_text("c" * 40)  # 10 tokens
    (agents / "services").mkdir()
    (agents / "services/AGENTS.md").write_text("d" * 4)  # 1 token

    def fields(name: str, extra: str = "") -> str:
        return f"name: {name}\ndescription: {'x' * 40}\n{extra}"  # 10 tokens each

    _skill(agents, "", "adr", fields("adr"))
    _skill(agents, "", "epic", fields("epic", "disable-model-invocation: true\n"))
    _skill(agents, "", "svc", fields("svc", "paths: services/**/*.py\n"))
    _skill(agents, "", "toml", fields("toml", "paths: ['**/pyproject.toml']\n"))
    (agents / "libs/.agents/skills/qa/SKILL.md").write_text(
        "---\n" + fields("qa", "user-invocable: false\n") + "---\n"
    )
    assert _budgets(agents) == {
        "": (120, 10),  # adr only
        "libs": (340, 30),  # adr, toml, qa
        "services": (141, 30),  # adr, svc, toml
    }


@pytest.mark.parametrize(
    "budget,expected",
    [
        (docs_check.Budget("", 4000, 1500), []),
        (
            docs_check.Budget("", 4001, 0),
            ["root session: 4001 tokens always on; the ceiling is 4000"],
        ),
        (docs_check.Budget("libs", 7000, 0), []),
        (
            docs_check.Budget("libs", 7001, 1501),
            [
                "libs/ session: 7001 tokens always on; the ceiling is 7000",
                "libs/ session: 1501 tokens of skill descriptions; the ceiling is 1500",
            ],
        ),
    ],
)
def test_budget_warnings(budget, expected):
    assert docs_check.budget_warnings([budget]) == expected


def test_budget_flag_prints_the_figures(agents, capsys):
    """A clean run stays quiet; `--budget` prints every session."""
    _stage(agents)
    _run(agents, capsys)
    _stage(agents)
    assert _run(agents, capsys) == (0, "")
    assert capsys.readouterr().out == ""
    docs_check.main(["--budget"], root=agents)
    assert capsys.readouterr().out.splitlines() == [
        "root: 5 tokens, 0 of them skill descriptions",
        "libs/: 14 tokens, 1 of them skill descriptions",
    ]


def test_skill_index(agents, capsys):
    """The catalogue lists root skills first, with scope and invocation."""
    _skill(agents, "", "adr", "name: adr\ndescription: Write an ADR.\n")
    _skill(
        agents,
        "",
        "release",
        "name: release\ndescription: Cut a | release.\n"
        "disable-model-invocation: true\n",
    )
    _skill(
        agents,
        "",
        "svc",
        "name: svc\ndescription: >\n  Change a\n  service.\npaths: [services/**]\n"
        "user-invocable: false\n",
    )
    _stage(agents)
    code, out = _run(agents, capsys)
    assert code == 1
    assert "docs/agent-skills.md: regenerated the index; stage the file" in out
    text = (agents / docs_check.SKILL_INDEX_FILE).read_text()
    start, end = (text.index(m) for m in docs_check.SKILL_INDEX_MARKS)
    assert text[start:end].splitlines()[1:] == [
        "| Skill | Applies | Invoked by | Description |",
        "|---|---|---|---|",
        "| [adr](../.agents/skills/adr/SKILL.md) | whole repo | model or `/adr` |"
        " Write an ADR. |",
        "| [release](../.agents/skills/release/SKILL.md) | whole repo | `/release` |"
        " Cut a \\| release. |",
        "| [svc](../.agents/skills/svc/SKILL.md) | `services/**` | model |"
        " Change a service. |",
        "| [qa](../libs/.agents/skills/qa/SKILL.md) | `libs/` | model or `/qa` |"
        " Do qa. |",
    ]
    _stage(agents)
    assert _run(agents, capsys) == (0, "")
