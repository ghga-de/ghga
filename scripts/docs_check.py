#!/usr/bin/env python3
"""Check the ADRs and the epics, and the references to them, across the tree (ADR-0041).

Without arguments it checks both sets: ADR file names, frontmatter, headings and
supersession, epic names and shape, the shape of the instruction files and skills for
coding agents, and every reference in the tracked text files. It then regenerates the
ADR index in docs/README.md, the epic index in docs/epics/README.md and the skill
catalogue in docs/agent-skills.md, and fails when that changed a file, so the fix is to
stage the result. A session's context budget over its ceiling is a warning, which leaves
the exit code alone; `--budget` prints every session's figures. With `--refs` it checks
only the references in the files given.

The rules are the ones in docs/style.md, docs/epics/README.md and
docs/agent-instructions.md; a change to one needs a change to the other.

Usage:
    uv run python scripts/docs_check.py
    uv run python scripts/docs_check.py --budget
    uv run python scripts/docs_check.py --refs README.md docs/conventions.md
"""

from __future__ import annotations

import argparse
import datetime
import os
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass, field

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
ADR_DIR = "docs/adrs"
ADR_INDEX_FILE = "docs/README.md"
TEMPLATE = "adr-template.md"
EPIC_DIR = "docs/epics"
EPIC_INDEX_FILE = "docs/epics/README.md"
EPIC_SPEC = "README.md"

STATUSES = ("proposed", "accepted", "rejected", "deprecated", "superseded")
TAGS = (
    "backend",
    "frontend",
    "data",
    "events",
    "security",
    "build",
    "release",
    "deploy",
    "testing",
    "docs",
    "process",
)
REQUIRED_FIELDS = ("status", "date", "tags")
REF_FIELDS = ("supersedes", "superseded-by", "related")
FIELDS = (*REQUIRED_FIELDS, "amended", *REF_FIELDS)
HEADINGS = (
    "## Summary",
    "## Details",
    "### Context",
    "### Decision",
    "### Consequences",
    "### Alternatives",
)

FILE_NAME = re.compile(r"^adr-(\d{4})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
TITLE = re.compile(r"^# ADR-(\d{4}) — (\S.*)$")
FRONTMATTER = re.compile(r"\A---\n(.*?\n)---\n", re.DOTALL)
REF_VALUE = re.compile(r"^ADR-(\d{4})$")

# `ADR-0028`, and the compound forms `ADR-0028/0035` and `ADR-0031`, en dash, `0035`. A
# tail of fewer than four digits is reported, since a two-digit tail is ambiguous.
REFERENCE = re.compile(r"\bADR-(\d{4})((?:[/\u2013]\d+)*)")
REFERENCE_TAIL = re.compile(r"[/\u2013](\d+)")
# A path into docs/adrs/ from anywhere, and a sibling link inside docs/adrs/ itself.
PATH_LINK = re.compile(r"\badrs/(adr-\d{4}-[a-z0-9-]+\.md)")
SIBLING_LINK = re.compile(r"\]\((adr-\d{4}-[a-z0-9-]+\.md)")

# An epic is a single Markdown file, or a directory holding README.md next to the
# supporting files that earned it the directory (docs/epics/README.md).
EPIC_NAME = re.compile(r"^epic-(\d{4})-[a-z0-9]+(?:-[a-z0-9]+)*$")
EPIC_TEMPLATE = re.compile(r"^epic-template-(?:exploratory|implementation)$")
EPIC_TITLE = re.compile(r"^# (\S.*\S) \(([^()]+)\)$")
EPIC_TYPE = re.compile(r"^\*\*Epic Type:\*\* (.+)$")
EPIC_TYPES = (
    "Exploratory Epic",
    "Implementation Epic",
    "Exploration and Implementation Epic",
)
# A link to an epic from inside docs/epics/, and one from anywhere else.
EPIC_SIBLING_LINK = re.compile(r"\]\((\.{1,2}/epic-[a-z0-9-]+(?:/README)?\.md)\)")
EPIC_PATH_LINK = re.compile(r"\bepics/(epic-[a-z0-9-]+(?:/README)?\.md)")

# Instruction files for coding agents (ADR-0042, docs/agent-instructions.md). Claude
# Code reads AGENTS.md only while no CLAUDE.md sits in the working directory or above
# it, so none may be committed. The Copilot stub points at AGENTS.md and holds nothing
# of its own, so it is allowed one heading and a few lines of prose.
CLAUDE_FILES = ("CLAUDE.md", "CLAUDE.local.md")
STUB_MAX_LINES = 6
STUB_CONTENT = re.compile(r"^(?:[-*+]\s|\d+\.\s|>|\||#{1,6}\s|```|@)")
COPILOT_STUB = ".github/copilot-instructions.md"
SKILL_DIR = ".agents/skills"
SKILL_FILE = "SKILL.md"
SKILL_PATH = re.compile(r"^(?:(.+)/)?\.agents/skills/([^/]+)/SKILL\.md$")
# Claude Code reads .claude/skills/ only, so each skill has a symlink there.
CLAUDE_SKILL_ENTRY = re.compile(r"^(?:(.+)/)?\.claude/skills/([^/]+)$")
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SKILL_NAME_MAX = 64
DESCRIPTION_MAX = 1024
DESCRIPTION_WARN = 300
# The six fields of the Agent Skills spec, then the Claude Code fields that only
# optimise and that the other tools ignore without harm.
SKILL_FIELDS = (
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
    "disable-model-invocation",
    "user-invocable",
    "paths",
)
LINK = re.compile(r"\]\(<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\)")
LINK_EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|#)")

# What the repo puts into a session before any task, at characters / 4: the root
# AGENTS.md, the output style, the AGENTS.md files down to the area, and the
# descriptions of the skills the model may invoke there (docs/agent-instructions.md).
OUTPUT_STYLE = ".claude/output-styles/ghga-dev.md"
CHARS_PER_TOKEN = 4
BUDGET_ROOT = 4000
BUDGET_AREA = 7000
BUDGET_DESCRIPTIONS = 1500
# Paths that were instruction files for one tool and that no tool reads here.
ORPHAN_DIRS = (".copilot/", ".github/instructions/", ".cursor/rules/")
ORPHAN_NAMES = (".cursorrules", ".clinerules", ".windsurfrules", ".aider.conf.yml")

ADR_INDEX_START = "<!-- adr-index:start -->"
ADR_INDEX_END = "<!-- adr-index:end -->"
# The epic index is two lists. Where an epic's line sits is the one part edited by
# hand: a line moved into the completed list stays there, and every other epic, a new
# one included, is listed as unfolding (docs/epics/README.md).
EPIC_COMPLETED_MARKS = (
    "<!-- epic-index:completed:start -->",
    "<!-- epic-index:completed:end -->",
)
EPIC_UNFOLDING_MARKS = (
    "<!-- epic-index:unfolding:start -->",
    "<!-- epic-index:unfolding:end -->",
)
EPIC_INDEX_LINK = re.compile(r"\]\(\./epic-(\d{4})-")
INDEX_EMPTY = "None at the moment.\n"
SKILL_INDEX_FILE = "docs/agent-skills.md"
SKILL_INDEX_MARKS = ("<!-- skill-index:start -->", "<!-- skill-index:end -->")

# Test data that holds broken ADRs and references on purpose, and skill eval cases, which
# name the ADRs a run is expected to create.
REF_EXCLUDED = ("scripts/tests/test_docs_check.py",)
REF_EXCLUDED_DIR = re.compile(r"(?:^|/)\.agents/skills/[^/]+/evals/")


@dataclass
class Adr:
    """One parsed ADR file."""

    name: str
    number: str
    title: str = ""
    meta: dict = field(default_factory=dict)

    def refs(self, key: str) -> list[str]:
        """Return the ADR numbers a reference field names, e.g. `["0024"]`."""
        values = self.meta.get(key) or []
        return [m.group(1) for v in values if (m := REF_VALUE.match(str(v)))]


@dataclass
class Epic:
    """One epic, as a single Markdown file or as a directory holding README.md."""

    name: str
    number: int
    path: str  # the spec, relative to docs/epics/
    title: str = ""
    code_name: str = ""
    type: str = ""


@dataclass
class Skill:
    """One skill, from the frontmatter of its SKILL.md."""

    name: str
    base: str  # the directory holding its .agents/, "" at the root
    path: str  # the SKILL.md, relative to the root
    description: str = ""
    paths: list[str] = field(default_factory=list)
    by_model: bool = True
    by_user: bool = True


@dataclass
class Budget:
    """The always-on context of a session started in one directory, in tokens."""

    area: str  # "" for the root
    total: int
    descriptions: int


def _split(text: str) -> tuple[dict | None, str]:
    """Split a file into its parsed frontmatter and the body after it."""
    match = FRONTMATTER.match(text)
    if not match:
        return None, text
    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        meta = "invalid"
    return meta if isinstance(meta, dict) else {"": meta}, text[match.end() :]


def _headings(body: str) -> list[str]:
    """Return the level-2 and level-3 headings outside fenced code blocks."""
    headings, fenced = [], False
    for line in body.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        elif not fenced and re.match(r"^#{2,3} ", line):
            headings.append(line.rstrip())
    return headings


def _check_headings(name: str, body: str) -> list[str]:
    """Require the template headings in order; only `###` may follow them."""
    headings = _headings(body)
    if headings[: len(HEADINGS)] != list(HEADINGS):
        return [f"{name}: headings must start with {', '.join(HEADINGS)}"]
    return [
        f"{name}: '{h}' after the template headings must be a ### subsection"
        for h in headings[len(HEADINGS) :]
        if not h.startswith("### ")
    ]


def _check_meta(adr: Adr, numbers: set[str]) -> list[str]:
    """Check the frontmatter fields and their values."""
    name, meta, problems = adr.name, adr.meta, []
    problems += [
        f"{name}: missing field '{k}'" for k in REQUIRED_FIELDS if k not in meta
    ]
    problems += [f"{name}: unknown field '{k}'" for k in meta if k not in FIELDS]
    if "status" in meta and meta["status"] not in STATUSES:
        problems.append(f"{name}: status '{meta['status']}' is not one of {STATUSES}")
    for key in ("date", "amended"):
        if key in meta and not isinstance(meta[key], datetime.date):
            problems.append(f"{name}: {key} must be a YYYY-MM-DD date")
    if "tags" in meta:
        tags = meta["tags"]
        if not isinstance(tags, list) or not tags:
            problems.append(f"{name}: tags must be a non-empty list")
        else:
            problems += [f"{name}: unknown tag '{t}'" for t in tags if t not in TAGS]
            if len(set(map(str, tags))) != len(tags):
                problems.append(f"{name}: tags repeat")
    return problems + _check_ref_fields(adr, numbers)


def _check_ref_fields(adr: Adr, numbers: set[str]) -> list[str]:
    """Check that `supersedes`, `superseded-by` and `related` name existing ADRs."""
    name, problems = adr.name, []
    for key in REF_FIELDS:
        if key not in adr.meta:
            continue
        values = adr.meta[key]
        if not isinstance(values, list) or not values:
            problems.append(f"{name}: {key} must be a non-empty list of ADR-NNNN")
            continue
        for value in values:
            match = REF_VALUE.match(str(value))
            if not match:
                problems.append(f"{name}: {key} value '{value}' is not ADR-NNNN")
            elif match.group(1) == adr.number:
                problems.append(f"{name}: {key} names the ADR itself")
            elif match.group(1) not in numbers:
                problems.append(f"{name}: {key} names {value}, which does not exist")
    return problems


def _check_supersession(adrs: dict[str, Adr]) -> list[str]:
    """Require `supersedes` and `superseded-by` to name each other."""
    problems = []
    for number, adr in adrs.items():
        by = adr.refs("superseded-by")
        if by and adr.meta.get("status") != "superseded":
            problems.append(
                f"{adr.name}: has superseded-by but status is not superseded"
            )
        if adr.meta.get("status") == "superseded" and not by:
            problems.append(f"{adr.name}: status superseded needs superseded-by")
        for other in by:
            if other in adrs and number not in adrs[other].refs("supersedes"):
                problems.append(
                    f"{adr.name}: superseded by ADR-{other}, which lacks "
                    f"supersedes: [ADR-{number}]"
                )
        for other in adr.refs("supersedes"):
            if other in adrs and number not in adrs[other].refs("superseded-by"):
                problems.append(
                    f"{adr.name}: supersedes ADR-{other}, which lacks "
                    f"superseded-by: [ADR-{number}]"
                )
    return problems


def load_adrs(root: pathlib.Path) -> tuple[dict[str, Adr], list[str]]:
    """Parse every ADR and check each file on its own and the set as a whole.

    Returns:
        The ADRs by number, the template excluded, and the problems found.
    """
    adr_dir = root / ADR_DIR
    adrs: dict[str, Adr] = {}
    problems: list[str] = []
    files = sorted(p for p in adr_dir.iterdir() if p.is_file())
    for path in files:
        name = path.name
        match = FILE_NAME.match(name)
        if not match and name != TEMPLATE:
            problems.append(f"{name}: file name is not adr-NNNN-kebab-case.md")
            continue
        meta, body = _split(path.read_text(encoding="utf-8"))
        problems += _check_headings(name, body)
        if not match:  # the template carries placeholders, not values
            continue
        number = match.group(1)
        if number in adrs:
            problems.append(f"{name}: number {number} is taken by {adrs[number].name}")
            continue
        adr = Adr(name, number)
        adrs[number] = adr
        first = body.lstrip("\n").split("\n", 1)[0]
        title = TITLE.match(first)
        if not title or title.group(1) != number:
            problems.append(f"{name}: first line must be '# ADR-{number} — Title'")
        else:
            adr.title = title.group(2).strip()
        if meta is None:
            problems.append(f"{name}: no YAML frontmatter")
        elif "" in meta:
            problems.append(f"{name}: frontmatter is not a YAML mapping")
        else:
            adr.meta = meta
    numbers = set(adrs)
    for adr in adrs.values():
        problems += _check_meta(adr, numbers)
    problems += _check_supersession(adrs)
    return adrs, problems


def check_references(
    root: pathlib.Path, paths: list[str], adr_names: set[str]
) -> list[str]:
    """Report ADR references in the given files that name no existing ADR.

    Args:
        root: The repository root the paths are relative to.
        paths: The files to scan; binary and missing files are skipped.
        adr_names: The file names in docs/adrs/, the template included.
    """
    numbers = {m.group(1) for n in adr_names if (m := FILE_NAME.match(n))}
    problems = []
    for rel in paths:
        if rel in REF_EXCLUDED or REF_EXCLUDED_DIR.search(rel):
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        in_adr_dir = rel.startswith(f"{ADR_DIR}/")
        if not (in_adr_dir or any(term in text for term in ("ADR-", "adrs/", "epic-"))):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            where = f"{rel}:{lineno}"
            problems += _line_problems(where, line, in_adr_dir, adr_names, numbers)
            problems += _epic_link_problems(where, line, rel, root)
    return problems


def _line_problems(
    where: str, line: str, in_adr_dir: bool, adr_names: set[str], numbers: set[str]
) -> list[str]:
    """Report the dangling ADR mentions and links in one line."""
    problems = []
    for match in REFERENCE.finditer(line):
        for part in [match.group(1), *REFERENCE_TAIL.findall(match.group(2))]:
            if len(part) != 4:
                problems.append(f"{where}: '{match.group(0)}' needs four-digit numbers")
            elif part not in numbers:
                problems.append(f"{where}: ADR-{part} does not exist")
    links = PATH_LINK.findall(line)
    if in_adr_dir:
        links += SIBLING_LINK.findall(line)
    problems += [
        f"{where}: link to {ADR_DIR}/{target}, which does not exist"
        for target in links
        if target not in adr_names
    ]
    return problems


def _epic_spec(base: pathlib.Path, entry: pathlib.Path) -> tuple[str | None, list[str]]:
    """Return the epic's spec path relative to docs/epics/, and the shape problems."""
    name = entry.name
    if entry.is_file():
        return name, []
    spec = entry / EPIC_SPEC
    problems = []
    if not spec.exists():
        problems.append(f"{name}: is a directory without {EPIC_SPEC}")
    if not any(p.name != EPIC_SPEC for p in entry.iterdir()):
        problems.append(
            f"{name}: is a directory with nothing but {EPIC_SPEC}; make it {name}.md"
        )
    return (f"{name}/{EPIC_SPEC}" if not problems else None), problems


def load_epics(root: pathlib.Path) -> tuple[list[Epic], list[str]]:
    """Parse every epic and check the names, the shape and the titles.

    Returns:
        The epics in number order, the templates excluded, and the problems found.
    """
    base = root / EPIC_DIR
    epics: dict[int, Epic] = {}
    problems: list[str] = []
    for entry in sorted(base.iterdir()):
        name = entry.name
        if entry.is_file() and name.endswith(".md"):
            name = name[: -len(".md")]
        if not name.startswith("epic-"):
            continue
        if (base / name).exists() and (base / f"{name}.md").exists():
            if entry.is_file():  # report the pair once
                problems.append(f"{name}: exists as a file and as a directory")
            continue
        if EPIC_TEMPLATE.match(name):
            problems += _epic_spec(base, entry)[1]
            continue
        match = EPIC_NAME.match(name)
        if not match:
            problems.append(f"{name}: name is not epic-NNNN-kebab-case")
            continue
        number = int(match.group(1))
        if number in epics:
            problems.append(
                f"{name}: number {number:04d} is taken by {epics[number].name}"
            )
            continue
        path, shape_problems = _epic_spec(base, entry)
        problems += shape_problems
        if path is None:
            continue
        epic = Epic(name, number, path)
        epics[number] = epic
        problems += _epic_header(base, epic)
    return [epics[n] for n in sorted(epics)], problems


def _epic_header(base: pathlib.Path, epic: Epic) -> list[str]:
    """Fill in the epic's description, code name and type from its first two fields."""
    lines = [
        line.rstrip()
        for line in (base / epic.path).read_text(encoding="utf-8").splitlines()
    ]
    problems = []
    heading = next((line for line in lines if line.startswith("# ")), "")
    match = EPIC_TITLE.match(heading)
    if not match:
        problems.append(
            f"{epic.name}: first heading must be '# Description (Code Name)'"
        )
    else:
        epic.title, epic.code_name = match.group(1), match.group(2).strip()
    kind = next((m for line in lines if (m := EPIC_TYPE.match(line))), None)
    if not kind:
        problems.append(f"{epic.name}: no '**Epic Type:** ...' line")
    elif kind.group(1) not in EPIC_TYPES:
        problems.append(
            f"{epic.name}: epic type '{kind.group(1)}' is not one of {EPIC_TYPES}"
        )
    else:
        epic.type = kind.group(1)
    return problems


def _continuous(epics: list[Epic]) -> bool:
    """Whether the epics are numbered without a gap."""
    return not epics or epics[-1].number - epics[0].number == len(epics) - 1


def render_epic_index(epics: list[Epic], ordered: bool) -> str:
    """Render one epic list, one line per epic in number order."""
    if not epics:
        return INDEX_EMPTY
    rows = []
    for epic in epics:
        link = f"[{epic.code_name}](./{epic.path})"
        head = f"{epic.number}." if ordered else f"- ({epic.number})"
        rows.append(f"{head} {link}: {epic.title}")
    return "\n".join(rows) + "\n"


def completed_epics(text: str) -> set[int]:
    """Return the numbers of the epics listed between the completed markers."""
    start_mark, end_mark = EPIC_COMPLETED_MARKS
    start, end = text.find(start_mark), text.find(end_mark)
    if start < 0 or end < start:
        return set()
    return {int(n) for n in EPIC_INDEX_LINK.findall(text[start:end])}


def render_epic_lists(
    epics: list[Epic], text: str
) -> list[tuple[str, tuple[str, str]]]:
    """Split the epics into the completed and the unfolding list.

    An ordered list only shows the right numbers when they have no gap, since Markdown
    counts on from the first. Both lists take the same style, so they read as one index.
    """
    done = completed_epics(text)
    completed = [e for e in epics if e.number in done]
    unfolding = [e for e in epics if e.number not in done]
    ordered = _continuous(completed) and _continuous(unfolding)
    return [
        (render_epic_index(completed, ordered), EPIC_COMPLETED_MARKS),
        (render_epic_index(unfolding, ordered), EPIC_UNFOLDING_MARKS),
    ]


def _epic_link_problems(
    where: str, line: str, rel: str, root: pathlib.Path
) -> list[str]:
    """Report the links to epics in one line that resolve to nothing."""
    base = (root / rel).parent
    targets = [base / t for t in EPIC_SIBLING_LINK.findall(line)]
    targets += [root / EPIC_DIR / t for t in EPIC_PATH_LINK.findall(line)]
    return [
        f"{where}: link to {os.path.relpath(path, root)}, which does not exist"
        for path in targets
        if not path.exists()
    ]


def render_index(adrs: dict[str, Adr]) -> str:
    """Render the index table, one row per ADR in number order."""

    def link(number: str) -> str:
        adr = adrs.get(number)
        return f"[{number}](adrs/{adr.name})" if adr else number

    rows = ["| # | Title | Status | Tags |", "|---|---|---|---|"]
    for number, adr in sorted(adrs.items()):
        status = str(adr.meta.get("status", ""))
        if by := adr.refs("superseded-by"):
            status += " by " + ", ".join(map(link, by))
        if supersedes := adr.refs("supersedes"):
            status += "; supersedes " + ", ".join(map(link, supersedes))
        tags = ", ".join(map(str, adr.meta.get("tags") or []))
        title = adr.title.replace("|", "\\|")
        rows.append(f"| {link(number)} | {title} | {status} | {tags} |")
    return "\n".join(rows) + "\n"


def update_index(text: str, table: str, start_mark: str, end_mark: str) -> str | None:
    """Replace the table between the index markers; None when a marker is missing."""
    start, end = text.find(start_mark), text.find(end_mark)
    if start < 0 or end < start:
        return None
    return f"{text[: start + len(start_mark)]}\n{table}{text[end:]}"


def _regenerate(
    root: pathlib.Path, rel: str, blocks: list[tuple[str, tuple[str, str]]]
) -> list[str]:
    """Write each block between its markers; report a missing marker or staging."""
    path = root / rel
    text = path.read_text(encoding="utf-8")
    updated = text
    for table, marks in blocks:
        result = update_index(updated, table, *marks)
        if result is None:
            return [f"{rel}: missing {marks[0]} or {marks[1]}"]
        updated = result
    if updated == text:
        return []
    path.write_text(updated, encoding="utf-8")
    return [f"{rel}: regenerated the index; stage the file"]


def _tracked(root: pathlib.Path) -> list[str]:
    """Return every tracked path, so a check can see the shape of the whole tree."""
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, capture_output=True, text=True
    )
    if result.returncode:
        raise RuntimeError(result.stderr)
    return [p for p in result.stdout.split("\0") if p]


def _stub_text(root: pathlib.Path, rel: str) -> str | None:
    """Return the stub's text, or None when git tracks it but the tree has it not.

    A half-applied rebase or a `git rm --cached` leaves that gap, and aborting the whole
    run on it would hide every other problem behind a traceback.
    """
    try:
        return (root / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _stub_problems(rel: str, text: str) -> list[str]:
    """Report content a pointer stub carries beyond a heading and a sentence."""
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return [f"{rel}: the stub is empty; it points at AGENTS.md"]
    problems = []
    if "AGENTS.md" not in text:
        problems.append(f"{rel}: the stub must point at AGENTS.md")
    headings = [line for line in lines if line.startswith("#")]
    if len(headings) > 1:
        problems.append(f"{rel}: a stub carries one heading, not {len(headings)}")
    for line in lines:
        if line not in headings and STUB_CONTENT.match(line):
            problems.append(f"{rel}: a stub carries no content of its own: {line!r}")
            break
    if len(lines) > STUB_MAX_LINES:
        problems.append(
            f"{rel}: the stub is {len(lines)} lines; at most {STUB_MAX_LINES},"
            " the rest belongs in the AGENTS.md beside it"
        )
    return problems


def check_instruction_files(root: pathlib.Path) -> list[str]:
    """Report instruction files that break the layout in docs/agent-instructions.md.

    No CLAUDE.md is committed, the Copilot stub carries nothing but a heading and a
    sentence, and no instruction file sits at a path no tool reads
    ([ADR-0042](docs/adrs/adr-0042-agent-instruction-files.md)).
    """
    tracked = _tracked(root)
    problems = [
        f"{rel}: a committed CLAUDE.md stops Claude Code reading AGENTS.md;"
        " move its rules into the AGENTS.md"
        for rel in tracked
        if pathlib.PurePosixPath(rel).name in CLAUDE_FILES
    ]
    if "AGENTS.md" in tracked:
        if COPILOT_STUB in tracked:
            if (text := _stub_text(root, COPILOT_STUB)) is not None:
                problems += _stub_problems(COPILOT_STUB, text)
        else:
            problems.append(
                f"{COPILOT_STUB}: missing; Copilot has no pointer to AGENTS.md"
            )

    for rel in tracked:
        if any(d in f"/{rel}" for d in ORPHAN_DIRS) or rel.endswith(ORPHAN_NAMES):
            problems.append(f"{rel}: an instruction file at a path no tool reads")
        elif rel.endswith(SKILL_FILE) and SKILL_DIR not in rel:
            problems.append(f"{rel}: a skill belongs under {SKILL_DIR}/<name>/")
    return sorted(problems)


def _body_links(body: str) -> list[str]:
    """Return the relative link targets outside fenced code blocks, without anchors."""
    targets, fenced = [], False
    for line in body.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced:
            targets += [
                t.split("#", 1)[0]
                for t in LINK.findall(line)
                if not LINK_EXTERNAL.match(t)
            ]
    return targets


def _skill_paths(value: object) -> list[str] | None:
    """Return `paths` as a list of globs; None when it is neither a string nor a list."""
    if isinstance(value, str):  # Claude Code also takes a comma-separated string
        return [p.strip() for p in value.split(",") if p.strip()]
    if isinstance(value, list) and all(isinstance(p, str) for p in value):
        return value
    return None


def _skill_meta(skill: Skill, meta: dict, directory: str) -> tuple[list, list]:
    """Check the frontmatter fields, fill in the skill and return problems, warnings."""
    rel, problems, warnings = skill.path, [], []
    name = meta.get("name")
    if name != directory:
        problems.append(f"{rel}: name {name!r} must equal its directory {directory!r}")
    elif len(name) > SKILL_NAME_MAX or not SKILL_NAME.match(name):
        problems.append(
            f"{rel}: name must be 1 to {SKILL_NAME_MAX} lowercase letters, digits"
            " and single hyphens"
        )
    description = meta.get("description")
    if not isinstance(description, str) or not description.strip():
        problems.append(f"{rel}: missing description")
    else:
        skill.description = " ".join(description.split())
        if len(skill.description) > DESCRIPTION_MAX:
            problems.append(
                f"{rel}: description is {len(skill.description)} characters;"
                f" at most {DESCRIPTION_MAX}"
            )
        elif len(skill.description) > DESCRIPTION_WARN:
            warnings.append(
                f"{rel}: description is {len(skill.description)} characters;"
                f" keep it under {DESCRIPTION_WARN}"
            )
    problems += [f"{rel}: unknown field '{k}'" for k in meta if k not in SKILL_FIELDS]
    for key in ("disable-model-invocation", "user-invocable"):
        if key in meta and not isinstance(meta[key], bool):
            problems.append(f"{rel}: {key} must be true or false")
    skill.by_model = meta.get("disable-model-invocation") is not True
    skill.by_user = meta.get("user-invocable") is not False
    if "paths" in meta:
        paths = _skill_paths(meta["paths"])
        if not paths:
            problems.append(f"{rel}: paths must be a glob or a list of globs")
        else:
            skill.paths = paths
    return problems, warnings


def load_skills(
    root: pathlib.Path, tracked: list[str]
) -> tuple[list[Skill], list[str], list[str]]:
    """Parse every tracked SKILL.md under an .agents/skills/<name>/ and check it.

    Returns:
        The skills, root ones first, then the problems and the warnings found.
    """
    skills, problems, warnings = [], [], []
    for rel in tracked:
        match = SKILL_PATH.match(rel)
        if not match or (text := _stub_text(root, rel)) is None:
            continue
        skill = Skill(match.group(2), match.group(1) or "", rel)
        meta, body = _split(text)
        if meta is None or "" in meta:
            problems.append(f"{rel}: frontmatter must be a YAML mapping between ---")
            continue
        found, warned = _skill_meta(skill, meta, match.group(2))
        problems += found
        warnings += warned
        base = (root / rel).parent
        problems += [
            f"{rel}: link to {target}, which does not exist"
            for target in _body_links(body)
            if target and not (base / target).exists()
        ]
        skills.append(skill)
    skills.sort(key=lambda s: (s.base, s.name))
    return skills, problems, warnings


def check_skill_links(root: pathlib.Path, tracked: list[str]) -> list[str]:
    """Report a skill without its .claude/skills/ symlink, and a symlink without its skill.

    The link sits beside the same .agents/ and is relative, so a clone gets it working
    without a setup step (docs/agent-instructions.md).
    """
    tracked_set, problems, expected = set(tracked), [], {}
    for rel in tracked:
        if match := SKILL_PATH.match(rel):
            prefix = f"{match.group(1)}/" if match.group(1) else ""
            name = match.group(2)
            expected[f"{prefix}.claude/skills/{name}"] = f"../../{SKILL_DIR}/{name}"
    for entry, target in expected.items():
        path = root / entry
        if entry not in tracked_set:
            problems.append(f"{entry}: missing; link it to {target}")
        elif not path.is_symlink() or os.readlink(path) != target:
            problems.append(f"{entry}: must be a symlink to {target}")
    problems += [
        f"{rel}: no skill at {SKILL_DIR}/{match.group(2)}"
        for rel in tracked
        if (match := CLAUDE_SKILL_ENTRY.match(rel)) and rel not in expected
    ]
    return sorted(problems)


def _within(path: str, base: str) -> bool:
    """Whether a directory is the base or below it; "" is the root."""
    return not base or path == base or path.startswith(f"{base}/")


def _glob_prefix(glob: str) -> str:
    """Return the directories of a glob before its first wildcard."""
    parts = []
    for part in glob.split("/")[:-1]:
        if any(c in part for c in "*?[{"):
            break
        parts.append(part)
    return "/".join(parts)


def _visible(skill: Skill, area: str) -> bool:
    """Whether the model is offered the skill in a session working in the area.

    A nested skill is offered at and below its directory. A root skill with `paths` is
    offered once the agent reads a matching file, so it counts wherever a match could be.
    """
    if not skill.by_model:
        return False
    if skill.base:
        return bool(area) and _within(area, skill.base)
    if not skill.paths:
        return True
    prefixes = [_glob_prefix(p) for p in skill.paths]
    return bool(area) and any(_within(area, p) or _within(p, area) for p in prefixes)


def context_budget(
    root: pathlib.Path, tracked: list[str], skills: list[Skill]
) -> list[Budget]:
    """Estimate the always-on context of a root session and of each area session.

    An area is a directory with an AGENTS.md or its own skills; its session also
    carries every AGENTS.md above it.
    """
    agents = {
        rel.removesuffix("AGENTS.md").rstrip("/"): rel
        for rel in tracked
        if pathlib.PurePosixPath(rel).name == "AGENTS.md"
    }
    areas = sorted({"", *agents, *(s.base for s in skills)})

    def chars(rel: str) -> int:
        return len(_stub_text(root, rel) or "") if rel in tracked_set else 0

    tracked_set, budgets = set(tracked), []
    for area in areas:
        files = [rel for base, rel in agents.items() if _within(area, base)]
        descriptions = sum(len(s.description) for s in skills if _visible(s, area))
        total = sum(map(chars, [*files, OUTPUT_STYLE])) + descriptions
        budgets.append(
            Budget(area, total // CHARS_PER_TOKEN, descriptions // CHARS_PER_TOKEN)
        )
    return budgets


def budget_warnings(budgets: list[Budget]) -> list[str]:
    """Report each session over its ceiling."""
    warnings = []
    for budget in budgets:
        where = f"{budget.area}/ session" if budget.area else "root session"
        ceiling = BUDGET_AREA if budget.area else BUDGET_ROOT
        if budget.total > ceiling:
            warnings.append(
                f"{where}: {budget.total} tokens always on; the ceiling is {ceiling}"
            )
        if budget.descriptions > BUDGET_DESCRIPTIONS:
            warnings.append(
                f"{where}: {budget.descriptions} tokens of skill descriptions;"
                f" the ceiling is {BUDGET_DESCRIPTIONS}"
            )
    return warnings


def render_budget(budgets: list[Budget]) -> str:
    """Render the budget figures, one session per line."""
    rows = []
    for budget in budgets:
        where = f"{budget.area}/" if budget.area else "root"
        rows.append(
            f"{where}: {budget.total} tokens, {budget.descriptions} of them"
            " skill descriptions"
        )
    return "\n".join(rows) + "\n"


def render_skill_index(skills: list[Skill]) -> str:
    """Render the skill catalogue, root skills first, then each nested set."""
    if not skills:
        return INDEX_EMPTY
    rows = ["| Skill | Applies | Invoked by | Description |", "|---|---|---|---|"]
    for skill in skills:
        if skill.base:
            applies = f"`{skill.base}/`"
        elif skill.paths:
            applies = ", ".join(f"`{p}`" for p in skill.paths)
        else:
            applies = "whole repo"
        invoked = [
            *(["model"] if skill.by_model else []),
            *([f"`/{skill.name}`"] if skill.by_user else []),
        ]
        description = skill.description.replace("|", "\\|")
        rows.append(
            f"| [{skill.name}](../{skill.path}) | {applies} |"
            f" {' or '.join(invoked) or 'nobody'} | {description} |"
        )
    return "\n".join(rows) + "\n"


def _tracked_files(root: pathlib.Path) -> list[str]:
    """Return the tracked text files that could hold a reference to an ADR or an epic."""
    result = subprocess.run(
        ["git", "grep", "-lzI", "-e", "ADR-", "-e", "adrs/", "-e", "epic-"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode > 1:  # 1 means no match
        raise RuntimeError(result.stderr)
    return [p for p in result.stdout.split("\0") if p]


def main(argv: list[str] | None = None, root: pathlib.Path = ROOT) -> int:
    """Run the set check or, with `--refs`, the reference check; return the exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--refs", nargs="*", metavar="FILE", help="check only references in FILE"
    )
    parser.add_argument(
        "--budget", action="store_true", help="print the context budget per session"
    )
    args = parser.parse_args(argv)

    adr_names = {p.name for p in (root / ADR_DIR).iterdir() if p.is_file()}
    warnings: list[str] = []
    if args.refs is not None:
        problems = check_references(root, args.refs, adr_names)
    else:
        adrs, problems = load_adrs(root)
        epics, epic_problems = load_epics(root)
        problems += epic_problems
        problems += check_instruction_files(root)
        tracked = _tracked(root)
        skills, skill_problems, warnings = load_skills(root, tracked)
        problems += skill_problems + check_skill_links(root, tracked)
        budgets = context_budget(root, tracked, skills)
        warnings += budget_warnings(budgets)
        if args.budget:
            print(render_budget(budgets), end="")
        # sibling links inside docs/adrs/ need none of the search terms
        paths = set(_tracked_files(root)) | {f"{ADR_DIR}/{n}" for n in adr_names}
        problems += check_references(root, sorted(paths), adr_names)
        problems += _regenerate(
            root,
            ADR_INDEX_FILE,
            [(render_index(adrs), (ADR_INDEX_START, ADR_INDEX_END))],
        )
        epic_index = (root / EPIC_INDEX_FILE).read_text(encoding="utf-8")
        problems += _regenerate(
            root, EPIC_INDEX_FILE, render_epic_lists(epics, epic_index)
        )
        problems += _regenerate(
            root,
            SKILL_INDEX_FILE,
            [(render_skill_index(skills), SKILL_INDEX_MARKS)],
        )

    for problem in problems:
        print(problem, file=sys.stderr)
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
