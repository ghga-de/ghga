#!/usr/bin/env python3
"""Check the ADRs in docs/adrs/ and the ADR references across the tree (ADR-0041).

Without arguments it checks the whole set: file names, frontmatter, headings,
supersession, and every ADR reference in the tracked text files. It then regenerates
the index in docs/README.md and fails when that changed the file, so the fix is to
stage the result. With `--refs` it checks only the references in the files given.

The rules for fields, statuses and tags are the ones in docs/style.md; a change to one
needs a change to the other.

Usage:
    uv run python scripts/adr_check.py
    uv run python scripts/adr_check.py --refs README.md docs/conventions.md
"""

from __future__ import annotations

import argparse
import datetime
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass, field

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
ADR_DIR = "docs/adrs"
INDEX_FILE = "docs/README.md"
TEMPLATE = "adr-template.md"

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

INDEX_START = "<!-- adr-index:start -->"
INDEX_END = "<!-- adr-index:end -->"

# Test data that holds broken ADRs and references on purpose.
REF_EXCLUDED = ("scripts/tests/test_adr_check.py",)


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
        if rel in REF_EXCLUDED:
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "ADR-" not in text and "adrs/" not in text and not rel.startswith(ADR_DIR):
            continue
        in_adr_dir = rel.startswith(f"{ADR_DIR}/")
        for lineno, line in enumerate(text.splitlines(), 1):
            problems += _line_problems(
                f"{rel}:{lineno}", line, in_adr_dir, adr_names, numbers
            )
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


def update_index(text: str, table: str) -> str | None:
    """Replace the table between the index markers; None when a marker is missing."""
    start, end = text.find(INDEX_START), text.find(INDEX_END)
    if start < 0 or end < start:
        return None
    return f"{text[: start + len(INDEX_START)]}\n{table}{text[end:]}"


def _tracked_files(root: pathlib.Path) -> list[str]:
    """Return the tracked text files that could hold an ADR reference."""
    result = subprocess.run(
        ["git", "grep", "-lzI", "-e", "ADR-", "-e", "adrs/"],
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
    args = parser.parse_args(argv)

    adr_names = {p.name for p in (root / ADR_DIR).iterdir() if p.is_file()}
    if args.refs is not None:
        problems = check_references(root, args.refs, adr_names)
    else:
        adrs, problems = load_adrs(root)
        # sibling links inside docs/adrs/ need neither search term
        paths = set(_tracked_files(root)) | {f"{ADR_DIR}/{n}" for n in adr_names}
        problems += check_references(root, sorted(paths), adr_names)
        index_path = root / INDEX_FILE
        text = index_path.read_text(encoding="utf-8")
        updated = update_index(text, render_index(adrs))
        if updated is None:
            problems.append(f"{INDEX_FILE}: missing {INDEX_START} or {INDEX_END}")
        elif updated != text:
            index_path.write_text(updated, encoding="utf-8")
            problems.append(f"{INDEX_FILE}: regenerated the ADR index; stage the file")

    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
