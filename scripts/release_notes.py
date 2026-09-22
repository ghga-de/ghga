#!/usr/bin/env python3
# Imports pypi_drift, whose idea of a member's shipped files decides which pull requests a
# library's notes list, and through it pypi_members, which needs `packaging` — so this
# script declares the same PEP 723 dependency and runs the same way, `uv run --script`.
# /// script
# requires-python = ">=3.11"
# dependencies = ["packaging>=25"]
# ///
"""Draft the release notes for a release tag (ADR-0043).

The notes have two parts. The summaries at the top, new features, changes and bug fixes,
are written by hand, so this script gives only their headings and a hint on what goes
under each. Below them it lists the pull requests merged since the previous release,
grouped by the commit type the commit grammar puts in front of each squash commit.

Each release lists only the pull requests that touched its own files. For the platform,
`ghga/X.Y.Z`, those are the services, the front end, the charts and the lock file. The
libraries and tools have notes of their own, so the platform's notes only name the ones
that changed, with their new version and a link to their release. A library or tool
lists the pull requests that changed what it ships, the files the drift gate checks.

Most of them have a `name/x.y.z` tag on the PyPI lane. The companions have none: they
are released with the platform, so drafting a platform release also tags each companion
with the platform version and drafts its release, unless nothing it ships has changed.

The previous release is the highest tag of the same name below this one. A final
release compares with the previous final release, a candidate with any earlier tag.

Usage (`uv run --script`, so the PEP 723 block above resolves):
    uv run --script scripts/release_notes.py ghga/15.4.0
    uv run --script scripts/release_notes.py hexkit/8.7.0 --previous hexkit/8.6.0
    uv run --script scripts/release_notes.py ghga/15.4.0 --draft   # companions too; `gh`
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass

import tomllib
from packaging.version import InvalidVersion, Version

from affected_targets import _canonical
from pypi_drift import shipped_prefixes
from pypi_members import _find_member, pypi_members

ROOT = pathlib.Path(__file__).resolve().parents[1]

PLATFORM = "ghga"

# What the platform release consists of. The lock file counts because a dependency update
# changes the images.
PLATFORM_PREFIXES = (
    "services/",
    "frontend/",
    "deploy/",
    # A service outside services/ until it moves there.
    "tools/auth-km-jobs/",
    "uv.lock",
)

# Members released with the platform that still get notes of their own, by tag name. Of
# metldata, the library counts here, while its chart and service belong to the platform.
COMPANIONS = {
    "metldata": "libs/metldata",
    "ghga-datasteward-kit": "tools/ghga-datasteward-kit",
}

# The commit types of the commit grammar (docs/conventions.md), in the order their
# pull requests are listed, each with its subheading.
PR_HEADINGS = {
    "feat": "Features",
    "fix": "Fixes",
    "docs": "Documentation",
    "refactor": "Refactoring",
    "test": "Tests",
    "chore": "Chores",
}

# Conventional Commits types the grammar does not use; it counts them as `chore`.
CHORE_ALIASES = {"perf", "ci", "build", "style"}

CONVENTIONAL = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<breaking>!)?:\s*(?P<text>.+)$"
)
PR_SUFFIX = re.compile(r"\s*\(#(?P<pr>\d+)\)$")
BREAKING_FOOTER = re.compile(r"^BREAKING[ -]CHANGE:", re.MULTILINE)

# The subject GitHub gives a merge commit. Squashing is the rule on `dev`, but hotfixes
# into `main` and some Renovate pull requests are merged this way.
MERGED_PR = re.compile(
    r"^Merge pull request #(?P<pr>\d+) from [^/\s]+/(?P<branch>\S+)$"
)

# A merge from one of these is a release merge or a back-merge, not a change of its own:
# the pull requests it brings in are listed one by one.
INTEGRATION_BRANCHES = {"dev", "main"}

INTRO = (
    "<!-- Summarise each section in a few short sentences for users: no pull request"
    " numbers, no minor changes or refactorings, and one item for a feature that spans"
    " several services or pull requests. Delete a section with nothing worth saying,"
    " and these comments. -->"
)


@dataclass(frozen=True)
class Entry:
    """One pull request, or one commit that came in without one."""

    kind: str
    scope: str | None
    text: str
    pr: int | None
    breaking: bool
    files: tuple[str, ...]


@dataclass(frozen=True)
class Summary:
    """One hand-written section at the top of the notes."""

    heading: str
    hint: str
    applies: Callable[[list[Entry]], bool]


SUMMARIES = (
    Summary(
        "New features",
        "<!-- What users can do now that they could not before. -->",
        lambda entries: any(e.kind == "feat" for e in entries),
    ),
    Summary(
        "Changes",
        "<!-- Changes in behaviour users will notice, breaking ones first. -->",
        lambda entries: any(
            e.kind not in {"feat", "fix"} or e.breaking for e in entries
        ),
    ),
    Summary(
        "Bug fixes",
        "<!-- The fixes users will notice. -->",
        lambda entries: any(e.kind == "fix" for e in entries),
    ),
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


def _parse_version(text: str) -> Version | None:
    try:
        return Version(text)
    except InvalidVersion:
        return None


def previous_tag(tag: str) -> str | None:
    """Finds the release a tag's notes compare with.

    Args:
        tag: The release tag, e.g. `ghga/15.4.0` or `hexkit/8.7.0`.

    Returns:
        The highest tag of the same name below `tag`, skipping release candidates
        unless `tag` is one itself; None when there is no earlier tag.
    """
    name, _, text = tag.rpartition("/")
    current = Version(text)
    earlier = {}
    for other in _git("tag", "--list", f"{name}/*").split():
        version = _parse_version(other.removeprefix(f"{name}/"))
        if version is None or version >= current:
            continue
        if version.is_prerelease and not current.is_prerelease:
            continue
        earlier[version] = other
    return earlier[max(earlier)] if earlier else None


def _branch_kind(branch: str) -> str:
    """Reads the commit type from a branch name such as `upload/feat/add-endpoints`."""
    for part in branch.split("/"):
        if part in PR_HEADINGS:
            return part
        if part == "hotfix":
            return "fix"
    return "chore"


def _entry(subject: str, body: str, files: list[str], kind: str = "chore") -> Entry:
    """Makes an entry from a commit subject or pull request title in the commit grammar.

    Args:
        subject: E.g. `feat(ucs)!: add UCS endpoints (#207)`.
        body: The rest of the message, searched for a `BREAKING CHANGE:` footer.
        files: The files the change touched.
        kind: The commit type to use when `subject` does not name one.
    """
    pr = None
    if match := PR_SUFFIX.search(subject):
        pr = int(match["pr"])
        subject = subject[: match.start()]
    scope, breaking, text = None, False, subject
    match = CONVENTIONAL.match(subject)
    if match and (match["type"] in PR_HEADINGS or match["type"] in CHORE_ALIASES):
        kind = match["type"] if match["type"] in PR_HEADINGS else "chore"
        scope, breaking, text = (
            match["scope"] or None,
            bool(match["breaking"]),
            match["text"],
        )
    breaking = breaking or bool(BREAKING_FOOTER.search(body))
    return Entry(kind, scope, text, pr, breaking, tuple(files))


def _merged_entry(
    match: re.Match[str], subject: str, body: str, files: list[str]
) -> Entry:
    """Makes an entry from a commit with GitHub's merge subject, using the PR title."""
    title = next((line for line in body.splitlines() if line.strip()), subject)
    return _entry(
        f"{title} (#{match['pr']})", body, files, _branch_kind(match["branch"])
    )


def entries(previous: str, tag: str) -> list[Entry]:
    """Lists the changes between two refs, oldest first.

    A pull request merged with a merge commit is one entry, and the commits it brought
    in are not listed again. Release merges and back-merges between `dev` and `main`
    are skipped, while the pull requests they bring in are listed.
    """
    log = _git(
        "log",
        "--reverse",
        "--name-only",
        "--format=%x1e%H%x1f%P%x1f%s%x1f%b%x1f",
        f"{previous}..{tag}",
    )
    commits: list[tuple[str, list[str], str, str, list[str]]] = []
    for record in log.split("\x1e")[1:]:
        sha, parent_list, subject, body, file_list = record.split("\x1f")
        commits.append((sha, parent_list.split(), subject, body, file_list.split()))

    merged: dict[str, Entry] = {}
    absorbed: set[str] = set()
    for sha, parents, subject, body, _ in commits:
        match = MERGED_PR.match(subject)
        if len(parents) != 2 or not match or match["branch"] in INTEGRATION_BRANCHES:
            continue
        absorbed.update(_git("rev-list", f"{parents[0]}..{parents[1]}").split())
        brought_in = _git("diff", "--name-only", parents[0], sha).split()
        merged[sha] = _merged_entry(match, subject, body, brought_in)

    result = []
    for sha, parents, subject, body, files in commits:
        if sha in merged:
            result.append(merged[sha])
        elif len(parents) == 1 and sha not in absorbed:
            # A squash that kept GitHub's merge subject still names its pull request.
            match = MERGED_PR.match(subject)
            if match:
                result.append(_merged_entry(match, subject, body, files))
            else:
                result.append(_entry(subject, body, files))
    return result


def select(changes: list[Entry], prefixes: tuple[str, ...]) -> list[Entry]:
    """Keeps the changes that touched a file under one of `prefixes`."""
    return [e for e in changes if any(f.startswith(prefixes) for f in e.files)]


def release_prefixes(name: str) -> tuple[str, ...]:
    """Finds the files a release of `name` consists of, e.g. `hexkit` or `ghga`.

    Raises:
        SystemExit: if `name` is neither the platform, a companion nor a PyPI-lane
            member, or what the member ships cannot be established.
    """
    if name == PLATFORM:
        return PLATFORM_PREFIXES
    path = COMPANIONS.get(name)
    if path is None:
        member = _find_member(name, pypi_members())
        if member is None:
            sys.exit(f"error: {name} is not the platform or a member with releases")
        path = member.path
    prefixes = shipped_prefixes(path)
    if not prefixes:
        sys.exit(f"error: cannot establish what {path} ships")
    return prefixes


def _member_version(ref: str, path: str) -> str | None:
    """Reads the version a member declares at `ref`, None if it did not exist there."""
    try:
        manifest = _git("show", f"{ref}:{path}/pyproject.toml")
    except subprocess.CalledProcessError:
        return None
    return tomllib.loads(manifest).get("project", {}).get("version")


def _components() -> dict[str, str]:
    """Maps the tag name of each library and tool to its path; the platform's are left out."""
    members = {}
    for root in ("libs", "tools"):
        for manifest in sorted((ROOT / root).glob("*/pyproject.toml")):
            path = str(manifest.parent.relative_to(ROOT))
            if f"{path}/".startswith(PLATFORM_PREFIXES):
                continue
            name = tomllib.loads(manifest.read_text())["project"]["name"]
            members[_canonical(name)] = path
    return members


def component_lines(previous: str, tag: str) -> list[str]:
    """Lists the libraries and tools whose shipped files changed for a platform release.

    Each shows its version at `tag`, linked to its release when that is tagged and the
    version is new. A companion takes the platform version, so it shows no earlier one.
    """
    changed = _git("diff", "--name-only", previous, tag).split()
    repo = os.environ.get("GITHUB_REPOSITORY", "ghga-de/ghga")
    platform_version = tag.rpartition("/")[2]
    lines = []
    for name, path in _components().items():
        prefixes = shipped_prefixes(path) or (f"{path}/",)
        if not any(f.startswith(prefixes) for f in changed):
            continue
        if name in COMPANIONS:
            now, before, note = platform_version, None, ""
        else:
            now = _member_version(tag, path) or "?"
            before = _member_version(previous, path)
            if before is None:
                note = " (new)"
            elif before == now:
                note = " (changed, same version)"
            else:
                note = f" (was {before})"
        label = f"{name} {now}"
        # Unbumped, the version's release predates these changes, so it is not linked.
        if before != now and _has_tag(f"{name}/{now}"):
            label = f"[{label}](https://github.com/{repo}/releases/tag/{name}/{now})"
        lines.append(f"- {label}{note}")
    return lines


def notes(tag: str, previous: str | None = None) -> tuple[str, bool]:
    """Writes the notes for `tag`, compared with `previous` or the previous tag.

    Returns:
        The notes, and whether there is anything to release: False only when there is
        a previous release and no pull request since changed what `tag` ships.
    """
    previous = previous or previous_tag(tag)
    if previous is None:
        return render(tag, None, []), True
    name = tag.rpartition("/")[0]
    changes = select(entries(previous, tag), release_prefixes(name))
    components = component_lines(previous, tag) if name == PLATFORM else []
    return render(tag, previous, changes, components), bool(changes)


def companion_releases(platform_tag: str) -> list[tuple[str, str, bool]]:
    """Tags the companions at a platform tag, locally, and writes their notes.

    A companion with nothing changed since its previous release is left out, and a tag
    made for it here is removed again.

    Returns:
        For each companion to release, its tag, its notes, and whether the tag was made
        here and so still has to be pushed.
    """
    version = platform_tag.rpartition("/")[2]
    releases = []
    for name in COMPANIONS:
        tag = f"{name}/{version}"
        created = not _has_tag(tag)
        if created:
            _git("tag", tag, f"{platform_tag}^{{commit}}")
        text, changed = notes(tag)
        if changed:
            releases.append((tag, text, created))
        elif created:
            _git("tag", "--delete", tag)
    return releases


def _has_tag(tag: str) -> bool:
    try:
        _git("rev-parse", "--verify", "--quiet", f"refs/tags/{tag}")
    except subprocess.CalledProcessError:
        return False
    return True


def _line(entry: Entry, name: str) -> str:
    # A library's own name as scope says nothing in that library's notes.
    scope = f"**{entry.scope}:** " if entry.scope and entry.scope != name else ""
    breaking = "**Breaking:** " if entry.breaking else ""
    text = entry.text[:1].upper() + entry.text[1:]
    pr = f" (#{entry.pr})" if entry.pr else ""
    return f"- {breaking}{scope}{text}{pr}"


def render(
    tag: str,
    previous: str | None,
    changes: list[Entry],
    components: list[str] | None = None,
) -> str:
    """Writes the notes: summary headings to fill in, the libraries and tools that
    changed, if given, then the pull requests by type."""
    name = tag.rpartition("/")[0]
    lines = [INTRO, ""]
    for summary in SUMMARIES:
        if previous is None or summary.applies(changes):
            lines += [f"## {summary.heading}", "", summary.hint, ""]
    if components:
        lines += ["## Libraries and tools", "", *components, ""]

    lines += ["## Pull requests", ""]
    if previous is None:
        lines += [f"No earlier `{name}/` release to compare with.", ""]
    elif not changes:
        lines += ["No pull request changed what this release ships.", ""]
    for kind, heading in PR_HEADINGS.items():
        # Stable, so the entries stay in merge order behind the breaking ones.
        group = sorted(
            (e for e in changes if e.kind == kind), key=lambda e: not e.breaking
        )
        if group:
            lines += [f"### {heading}", "", *(_line(e, name) for e in group), ""]
    return "\n".join(lines)


def draft(tag: str, text: str) -> None:
    """Creates the draft release for `tag`, leaving an existing release untouched.

    Only the platform's final releases may become the repository's latest release;
    otherwise a library release would take that badge from the platform.
    """
    exists = (
        subprocess.run(
            ["gh", "release", "view", tag], cwd=ROOT, capture_output=True
        ).returncode
        == 0
    )
    if exists:
        print(f"{tag} already has a release, left as it is")
        return
    name, _, text = tag.rpartition("/")
    prerelease = Version(text).is_prerelease
    title = f"GHGA {text}" if name == PLATFORM else f"{name} {text}"
    latest = name == PLATFORM and not prerelease
    command = [
        "gh", "release", "create", tag,
        "--draft", "--verify-tag",
        "--title", title,
        "--notes-file", "-",
        f"--latest={str(latest).lower()}",
    ]  # fmt: skip
    if prerelease:
        command.append("--prerelease")
    subprocess.run(command, cwd=ROOT, input=text, text=True, check=True)
    print(f"drafted the release {title} for {tag}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("tag", help="the release tag, e.g. ghga/15.4.0 or hexkit/8.7.0")
    parser.add_argument(
        "--previous",
        help="the ref to compare with, instead of the previous tag of the same name",
    )
    parser.add_argument(
        "--draft",
        action="store_true",
        help="create the draft GitHub release instead of printing the notes; for a"
        " platform tag, also tag and draft the companions",
    )
    args = parser.parse_args(argv)

    name, _, version = args.tag.rpartition("/")
    if not name or name == "packages" or _parse_version(version) is None:
        sys.exit(f"error: {args.tag} is not a release tag of the platform or a member")
    release_prefixes(name)
    if not _has_tag(args.tag):
        sys.exit(f"error: no tag {args.tag} in this clone")

    if not args.draft:
        print(notes(args.tag, args.previous)[0], end="")
        return 0
    # The companions are tagged first, so that the platform's notes can link them.
    companions = companion_releases(args.tag) if name == PLATFORM else []
    draft(args.tag, notes(args.tag, args.previous)[0])
    for tag, companion_text, created in companions:
        if created:
            # Pushed with the workflow token, the tag starts no release run.
            _git("push", "origin", f"refs/tags/{tag}")
        draft(tag, companion_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
