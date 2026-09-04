#!/usr/bin/env python3
# The only non-stdlib import is `packaging`, which owns the PEP 440 comparison deciding
# what gets uploaded. PEP 723 inline metadata declares it here rather than in the calling
# workflows: run this with `uv run --script`, which resolves the block into a throwaway
# environment. The jobs that call it never `uv sync`, so a bare `python3` has nothing to
# import.
# /// script
# requires-python = ">=3.11"
# dependencies = ["packaging>=25"]
# ///
"""Enumerate the PyPI-lane workspace members and the published-combo test matrix.

Single source of truth for pypi-matrix.yaml and pypi-publish.yaml. Lane membership
follows ADR-0014.

What needs releasing is decided against the *index*: a member is a release candidate
when the version it declares is above the latest one on PyPI. A version bump is the
release trigger.

A bare `--plan` sweeps: every candidate, ordered dependencies-first. `--target` instead
releases the single member a `name/x.y.z` tag asked for, and refuses when that member's
own closure is waiting to be released too — see `release_plan`.

Usage (`uv run --script`, so the PEP 723 block above resolves):
    uv run --script scripts/pypi_members.py --check-pypi        # test matrix cells (json)
    uv run --script scripts/pypi_members.py --members           # lane members only
    uv run --script scripts/pypi_members.py --paths libs/hexkit # restrict to given members
    uv run --script scripts/pypi_members.py --dev-requirements  # shared test deps
    uv run --script scripts/pypi_members.py --candidates        # unreleased versions
    uv run --script scripts/pypi_members.py --plan              # ordered plan + errors
    uv run --script scripts/pypi_members.py --plan --target hexkit   # that member alone

"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.request
from typing import NamedTuple

import tomllib
from packaging.version import InvalidVersion, Version

from affected_targets import _canonical, internal_dep_graph

# The versions the matrix runs on.
TEST_PYTHONS = ("3.11", "3.12", "3.13", "3.14")

# Directory defaults for the release lane (ADR-0014).
LANE_DEFAULTS = {"libs": "pypi", "tools": "none", "services": "platform"}

# A cell only runs tests, so formatting tools excluded
NON_TEST_TOOLS = ("ruff", "mypy", "pre-commit")

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _requirement_name(spec: str) -> str:
    """The package name in a requirement, e.g. `pytest>=9.1` -> `pytest`."""
    for i, ch in enumerate(spec):
        if ch in "<>=!~[ ;(":
            return spec[:i].strip().lower()
    return spec.strip().lower()


def _parse_version(text: str) -> tuple[int, ...]:
    """Converts a Python version into comparable numbers, e.g. `3.12` -> `(3, 12)`."""
    parts = []
    for chunk in text.strip().split("."):
        if chunk == "*":
            break
        digits = "".join(c for c in chunk if c.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts)


def _compare(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    """Compares two versions: -1 if left is older, 0 if equal, 1 if newer."""
    width = max(len(left), len(right))
    left = left + (0,) * (width - len(left))
    right = right + (0,) * (width - len(right))
    return (left > right) - (left < right)


def _satisfies_clause(version: tuple[int, ...], clause: str) -> bool:
    """Whether an (X, Y) Python version satisfies one requires-python clause."""
    clause = clause.strip()
    for op in (">=", "<=", "==", "!=", "~=", ">", "<"):
        if clause.startswith(op):
            bound_text = clause[len(op) :].strip()
            bound = _parse_version(bound_text)
            if not bound:
                return True
            if op == ">=":
                return _compare(version, bound) >= 0
            if op == "<=":
                return _compare(version, bound) <= 0
            if op == ">":
                return _compare(version, bound) > 0
            if op == "<":
                return _compare(version, bound) < 0
            if op in ("==", "!="):
                # Compare only the components the clause pins, so `== 3.12.*` and
                # `== 3.12` both match any 3.12 release.
                depth = min(len(version), len(bound))
                equal = _compare(version[:depth], bound[:depth]) == 0
                return equal if op == "==" else not equal
            if len(bound) < 2:
                return _compare(version, bound) >= 0
            upper = (*bound[:-2], bound[-2] + 1)
            return _compare(version, bound) >= 0 and _compare(version, upper) < 0
    return True


def _supported(requires_python: str, python: str) -> bool:
    """Whether `python` satisfies a whole requires-python specifier set."""
    if not requires_python:
        return True
    version = _parse_version(python)
    return all(
        _satisfies_clause(version, clause)
        for clause in requires_python.split(",")
        if clause.strip()
    )


def _test_extras(optional: dict) -> list[str]:
    """Returns the names of a member's optional dependency groups, i.e. its extras.

    Skips any extra that contains a NON_TEST_TOOLS entry — that is a dev extra, and a
    cell installs every extra it gets back.
    """
    return sorted(
        name
        for name, specs in optional.items()
        if not any(
            isinstance(spec, str) and _requirement_name(spec) in NON_TEST_TOOLS
            for spec in specs
        )
    )


def _closure(member_path: str, dependency_graph: dict[str, set[str]]) -> list[str]:
    """The transitive dependencies of one member.

    Args:
        member_path:
            The member's folder relative to the repo root, e.g. `libs/hexkit`
        dependency_graph:
            Every member's direct dependencies on other members, keyed the same way.
            Built by `internal_dep_graph()`.
    """
    seen: set[str] = set()
    queue = list(dependency_graph.get(member_path, ()))
    while queue:
        dep = queue.pop()
        if dep in seen:
            continue
        seen.add(dep)
        queue.extend(dependency_graph.get(dep, ()))
    return sorted(seen)


def _lane(root: str, ghga_markers: dict) -> str:
    """The member's release lane: its `[tool.ghga] release`, else LANE_DEFAULTS by folder.

    Args:
        root:
            The member's top-level folder: `libs`, `tools` or `services`.
        ghga_markers:
            The member's parsed `[tool.ghga]` table, e.g. `{"release": "pypi"}`, or
            empty when it declares none.
    """
    lane = ghga_markers.get("release")
    if lane:
        return lane
    if ghga_markers.get("pypi"):
        return "pypi"
    return LANE_DEFAULTS.get(root, "none")


def pypi_members(
    member_paths: list[str] | None = None, release_member_paths: set[str] | None = None
) -> list[dict]:
    """Returns one dict per PyPI-lane member, for the matrix and the release plan.

    Args:
        member_paths:
            Restrict to these member folders; None means every lane member.
        release_member_paths:
            The folders of the members being released in this same run. Does not
            restrict the result — it only fills in each member's `train_deps`.

    Returns:
        One dict per member with `path`, `package`, `version`, `requires_python`,
        `internal_deps`, `train_deps`, `extras`, and `pythons`
    """
    dependency_graph = internal_dep_graph()
    members = []
    for root in ("libs", "tools", "services"):
        directory = ROOT / root
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir()):
            manifest = path / "pyproject.toml"
            if not manifest.is_file():
                continue
            relative = str(path.relative_to(ROOT))
            if member_paths and relative not in member_paths:
                continue
            member_pyproject = tomllib.loads(manifest.read_text())
            ghga_markers = member_pyproject.get("tool", {}).get("ghga", {})

            if _lane(root, ghga_markers) != "pypi":
                continue
            project = member_pyproject["project"]
            requires_python = project.get("requires-python", "")
            closure = _closure(relative, dependency_graph)
            members.append(
                {
                    "path": relative,
                    "package": project["name"],
                    "version": project.get("version", ""),
                    "requires_python": requires_python,
                    "internal_deps": closure,
                    "train_deps": sorted(  # Dependencies released in this run.
                        d for d in closure if d in (release_member_paths or ())
                    ),
                    "extras": _test_extras(project.get("optional-dependencies", {})),
                    "pythons": [
                        p for p in TEST_PYTHONS if _supported(requires_python, p)
                    ],
                }
            )
    return members


def matrix_cells(members: list[dict]) -> list[dict]:
    """Creates the test matrix, each cell denoting one member on one Python version."""
    return [
        {
            "path": member["path"],
            "package": member["package"],
            "extras": ",".join(member["extras"]),
            # Only the closure being released alongside this member goes into the
            # wheelhouse. Its other dependencies resolve from the index.
            "train_deps": " ".join(member["train_deps"]),
            "python": python,
        }
        for member in members
        for python in member["pythons"]
    ]


def dev_requirements() -> list[str]:
    """Returns the root dev group with the lint/type tooling (NON_TEST_TOOLS) dropped."""
    root_pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    dev_dependencies = root_pyproject.get("dependency-groups", {}).get("dev", [])
    return [
        spec
        for spec in dev_dependencies
        if isinstance(spec, str) and _requirement_name(spec) not in NON_TEST_TOOLS
    ]


def _pypi_project(package: str) -> dict:
    """Queries PyPI's JSON API for what the index knows about one package.

    Returns `versions` (everything ever released under that name), `latest` (the latest
    stable release) and `reachable`. reachable=False means the query failed, not that the
    project is new — the callers treat the two differently.
    """
    url = f"https://pypi.org/pypi/{package}/json"
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            pypi_response = json.load(response)
    except urllib.error.HTTPError as error:
        # 404 means nothing of this name has ever been published.
        if error.code == 404:
            return {"reachable": True, "versions": set(), "latest": None}
        return {"reachable": False, "versions": set(), "latest": None}
    except OSError:
        return {"reachable": False, "versions": set(), "latest": None}
    return {
        "reachable": True,
        "versions": set(pypi_response.get("releases", {})),
        "latest": pypi_response.get("info", {}).get("version"),
    }


def _is_newer(candidate: str, other: str) -> bool:
    """Compares two version strings, returning True when `candidate` is the newer one.

    Ordering is delegated to `packaging`.
    """
    try:
        return Version(candidate) > Version(other)
    except InvalidVersion:
        return False


class Candidates(NamedTuple):
    """What the index says should happen to each lane member.

    The three lists partition the lane, so they are passed around together rather than
    separately. Handing a consumer only some of them is what let a member fall through
    every table unreported.
    """

    publishing: list[dict]
    skipped: list[dict]
    unreachable: list[dict]


def release_candidates(lane: list[dict] | None = None) -> Candidates:
    """Asks the index about every lane member and sorts them by what should happen.

    Args:
        lane:
            The lane members to ask about, when the caller has already enumerated them.
            `None` enumerates them here. Enumerating is not cheap — it parses every
            workspace pyproject and walks the dependency graph.

    Returns:
        A `Candidates`, in which every member lands in exactly one list. All carry the
        member dicts from `pypi_members` plus `pypi_latest` and `index_unreachable`; a
        skipped member also carries the `reason` it was passed over. `release_plan` turns
        each unreachable member into an error.

    Consequences worth naming:
    - a version already on PyPI is dropped here, so a re-run never attempts to
      republish it. Nothing checks TestPyPI, so a member stranded there collides on
      the rehearsal.
    - a member trailing the index (`ghga-validator` declares 1.1.1 while PyPI serves
      1.2.0, because upstream kept releasing) is *skipped*, not an error.
    """
    publishing, skipped, unreachable = [], [], []
    for member in lane if lane is not None else pypi_members():
        version = member["version"]
        project = _pypi_project(member["package"])
        if not project["reachable"]:
            unreachable.append(dict(member, pypi_latest=None, index_unreachable=True))
            continue
        member = dict(member, pypi_latest=project["latest"], index_unreachable=False)
        latest = project["latest"]
        if not version:
            skipped.append(dict(member, reason="declares no version"))
        elif version in project["versions"]:
            # Catches the case `latest` cannot: a prerelease is on the index but is not
            # the latest *stable*.
            skipped.append(dict(member, reason=f"{version} is already on the index"))
        elif latest and not _is_newer(version, latest):
            skipped.append(
                dict(member, reason=f"{version} is not above the released {latest}")
            )
        else:
            publishing.append(member)
    return Candidates(publishing, skipped, unreachable)


def _publish_order(members: list[dict]) -> list[dict]:
    """Sorts the release set so each member is published after the ones it depends on."""
    by_path = {member["path"]: member for member in members}
    return sorted(
        members,
        key=lambda member: (
            len([d for d in member["internal_deps"] if d in by_path]),
            member["path"],
        ),
    )


def _find_member(target: str, members: list[dict]) -> dict | None:
    """Locates one lane member by its path or its distribution name.

    Accepts both a distribution name (`hexkit`) and a path (`libs/hexkit`). Names are
    normalized, e.g. `ghga-connector` equals `ghga_connector`. Only the name form ever
    arrives from a tag — `name/x.y.z` leaves no `/` in the name — so the path form is
    for running this script by hand.
    """
    for member in members:
        if member["path"] == target:
            return member
    normalized_target_name = _canonical(target)
    for member in members:
        if _canonical(member["package"]) == normalized_target_name:
            return member
    return None


def _blocked_message(target: dict, blockers: list[dict]) -> str:
    """Explains why one member cannot be released alone, and how else to release it.

    Both remedies are spelled out as tags that can be pushed as-is, the ordered one in
    dependency order.
    """
    ordered = _publish_order(blockers)
    described = [
        f"{m['package']} ({m['version']} declared, PyPI serves"
        f" {m['pypi_latest'] or 'nothing'})"
        for m in ordered
    ]
    named = " and ".join(filter(None, [", ".join(described[:-1]), described[-1]]))
    tags = ", ".join(f"{_canonical(m['package'])}/{m['version']}" for m in ordered)
    return (
        f"{target['package']}: cannot be released on its own — it depends on"
        f" release candidate(s) {named}. Either push `pypi_sweep/x.y.z` to release"
        " the whole train dependencies-first, or release each dependency on its own tag"
        f" first, in this order: {tags}, then"
        f" {_canonical(target['package'])}/{target['version']}."
    )


def _targeted_plan(
    target: str,
    lane: list[dict],
    candidates: Candidates,
) -> tuple[list[dict], list[dict], list[str]]:
    """Narrows a sweep to the single member a `name/x.y.z` tag named.

    Args:
        target:
            The distribution name (or member folder) the tag named.
        lane:
            Every PyPI-lane member, used to resolve the target's name.
        candidates:
            What the sweep would have done — the *whole* set, not one already narrowed to
            the target. That is what makes the closure check below able to see anything:
            against a one-member set it would pass unconditionally. Its `unreachable` list
            separates a target with nothing to publish from one whose state is unknown.

    Returns:
        `(publishing, deselected, errors)`. `deselected` carries the candidates this tag
        excluded, each with its own `reason`, so every lane member still lands in exactly
        one of the plan's two tables. A non-empty `errors` always comes with an empty
        `publishing`: a targeted tag that cannot be honoured publishes nothing rather
        than falling back to the sweep nobody asked for.
    """
    member = _find_member(target, lane)
    if member is None:
        known = ", ".join(sorted(m["package"] for m in lane))
        return [], [], [f"{target} is not a PyPI-lane member (lane: {known})"]

    publishing = candidates.publishing
    selected = [m for m in publishing if m["path"] == member["path"]]
    if not selected:
        # An unreachable index says nothing about whether this member needs releasing.
        # release_plan already reports that, so a second guess here would contradict it.
        if any(m["path"] == member["path"] for m in candidates.unreachable):
            return [], [], []
        # State why the target was not selected.
        reason = next(
            (s["reason"] for s in candidates.skipped if s["path"] == member["path"]),
            "it is not a release candidate",
        )
        return [], [], [f"{member['package']}: nothing to publish — {reason}"]

    blockers = [m for m in publishing if m["path"] in member["internal_deps"]]
    if blockers:
        return [], [], [_blocked_message(member, blockers)]

    # Candidates a sweep would have released but this targeted run excludes.
    deselected = [
        dict(m, reason=f"the tag targeted {member['package']}")
        for m in publishing
        if m["path"] != member["path"]
    ]
    return selected, deselected, []


def release_plan(target: str | None = None) -> dict:
    """Builds the release plan the publish workflow runs on.

    Takes the release candidates, orders them dependencies-first so a tool never reaches
    PyPI before the library version it needs, and collects anything that makes the run
    unsafe to start.

    Args:
        target:
            Release only this member (a distribution name or a member folder), as a
            `name/x.y.z` tag asks for. `None` sweeps: every candidate goes out together.

    Returns:
        A dict with `members` (the ordered release set), `paths` (their folders),
        `skipped` (package, version and reason for each member passed over) and `errors`.
        A non-empty `errors` means publish nothing — the caller fails the job.
    """
    # Enumerated once and threaded through. Every helper below needs the same lane, and
    # building it parses every workspace pyproject and walks the dependency graph.
    lane = pypi_members()
    candidates = release_candidates(lane)
    publishing, skipped = candidates.publishing, candidates.skipped
    lane_paths = {member["path"] for member in lane}
    errors = []

    for member in candidates.unreachable:
        errors.append(
            f"{member['package']}: could not reach PyPI to establish what is already"
            f" released — refusing to plan a release against an unknown index"
        )

    # The whole sweep goes in and a narrowed set comes back. That order is load-bearing:
    # hand over an already-narrowed list and the closure check inside has only the target
    # to compare against, so it passes unconditionally.
    if target is not None:
        publishing, deselected, target_errors = _targeted_plan(target, lane, candidates)
        errors.extend(target_errors)
        skipped = [*skipped, *deselected]

    for member in publishing:
        for dep in member["internal_deps"]:
            if dep not in lane_paths:
                errors.append(
                    f"{member['package']}: internal dependency {dep} is not in the PyPI"
                    " lane, so consumers could never install it"
                )

    # `train_deps` is the part of a member's closure that ships in this same run, so it
    # is built from the repo rather than resolved from the index. Derived after the
    # narrowing, so a targeted member's comes out empty on its own: nothing else ships in
    # that run, so every internal dependency resolves from PyPI.
    release_member_paths = {member["path"] for member in publishing}
    ordered = _publish_order(
        [
            dict(
                m,
                train_deps=sorted(
                    d for d in m["internal_deps"] if d in release_member_paths
                ),
            )
            for m in publishing
        ]
    )
    return {
        "members": ordered,
        "paths": [member["path"] for member in ordered],
        "skipped": [
            {"package": m["package"], "version": m["version"], "reason": m["reason"]}
            for m in skipped
        ],
        "errors": errors,
    }


def _reject_ignored_flags(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> None:
    """Fails on a flag combination where one of the flags would be silently ignored.

    The mutually exclusive group already refuses two output modes at once. What is left
    is a modifier the chosen mode never reads, which would otherwise promise a narrowing
    that does not happen.
    """
    # `is not None` rather than a truth test, so `--target ""` is caught here instead of
    # reaching release_plan and failing with a misleading "not a PyPI-lane member".
    if args.target is not None:
        if not args.plan:
            parser.error("--target only applies to --plan")
        if not args.target:
            parser.error("--target needs a package name")

    # The plan always asks the index about every lane member, because the closure check
    # has to see candidates outside whatever the caller narrowed to. Neither flag can
    # reach it.
    if args.plan and (args.paths or args.check_pypi):
        parser.error(
            "--plan takes only --target; --paths and --check-pypi shape the cells"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--paths", nargs="*", help="restrict to these member paths (default: all)"
    )
    # Each of these prints one thing and stops, so asking for two is a contradiction.
    # argparse rejects the combination before main() runs, which also means the branches
    # below no longer decide the winner by their order. Passing none is still valid and
    # emits the matrix cells. `--paths`, `--target` and `--check-pypi` stay outside the
    # group because they modify a mode rather than being one.
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--members", action="store_true", help="emit lane members instead of cells"
    )
    mode.add_argument(
        "--dev-requirements",
        action="store_true",
        help="print the test dependencies, one per line",
    )
    mode.add_argument(
        "--candidates",
        action="store_true",
        help="emit members whose declared version is ahead of the index",
    )
    mode.add_argument(
        "--plan",
        action="store_true",
        help="emit the release plan: ordered members, paths, skips and errors",
    )
    parser.add_argument(
        "--target",
        help="with --plan: release only this member (distribution name or folder)"
        " instead of every candidate",
    )
    parser.add_argument(
        "--check-pypi",
        action="store_true",
        help="ask the index which members are being released, so cells build that"
        " closure from the repo instead of resolving it from PyPI",
    )
    args = parser.parse_args(argv)
    _reject_ignored_flags(parser, args)

    if args.dev_requirements:
        print("\n".join(dev_requirements()))
        return 0
    if args.plan:
        print(json.dumps(release_plan(args.target)))
        return 0
    if args.candidates:
        candidates = release_candidates()
        # No errors channel here, so an unanswerable index is an exit code instead.
        if candidates.unreachable:
            sys.exit(
                "error: could not reach PyPI to establish what is already released"
            )
        print(json.dumps(candidates.publishing))
        return 0

    release_member_paths = set()
    if args.check_pypi:
        candidates = release_candidates()
        if candidates.unreachable:
            sys.exit(
                "error: could not reach PyPI to establish what is already released"
            )
        release_member_paths = {m["path"] for m in candidates.publishing}

    members = pypi_members(args.paths, release_member_paths=release_member_paths)
    print(json.dumps(members if args.members else matrix_cells(members)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
