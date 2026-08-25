#!/usr/bin/env python3
"""Enumerate the PyPI-lane workspace members and the published-combo test matrix.

Single source of truth for pypi-matrix.yaml and pypi-publish.yaml. Lane membership
follows ADR-0014.

What needs releasing is decided against the *index*: a member is a release candidate
when the version it declares is above the latest one on PyPI. A version bump is the
release trigger.

Usage:
    python scripts/pypi_members.py --check-pypi         # test matrix cells (json)
    python scripts/pypi_members.py --members            # lane members only
    python scripts/pypi_members.py --paths libs/hexkit  # restrict to given members
    python scripts/pypi_members.py --dev-requirements       # shared test deps
    python scripts/pypi_members.py --candidates         # members whose version is unreleased
    python scripts/pypi_members.py --plan               # ordered release plan + errors

"""

from __future__ import annotations

import argparse
import functools
import json
import pathlib
import re
import sys

import tomllib

from affected_targets import internal_dep_graph

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
    member_paths: list[str] | None = None, release_members: set[str] | None = None
) -> list[dict]:
    """Returns one dict per PyPI-lane member, for the matrix and the release plan.

    Args:
        member_paths:
            Restrict to these member folders; None means every lane member.
        release_members:
            The members being released in this same run.

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
            data = tomllib.loads(manifest.read_text())
            ghga_markers = data.get("tool", {}).get("ghga", {})

            if _lane(root, ghga_markers) != "pypi":
                continue
            project = data["project"]
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
                        d for d in closure if d in (release_members or ())
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
    """What a bare environment needs to run a member's suite.

    The root dev group minus lint/type tooling (NON_TEST_TOOLS). Everything else a member's
    tests need is declared in its own pyproject and comes in with the wheel's extras.
    """
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    group = data.get("dependency-groups", {}).get("dev", [])
    return [
        spec
        for spec in group
        if isinstance(spec, str) and _requirement_name(spec) not in NON_TEST_TOOLS
    ]


@functools.cache
def _pypi_project(package: str) -> dict:
    """What the index knows: every released version, and the latest stable one.

    reachable=False means the query failed, not that the project is new — the callers
    treat the two differently.
    """
    import urllib.error
    import urllib.request

    url = f"https://pypi.org/pypi/{package}/json"
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        # 404 is an answer: nothing of this name has ever been published.
        if error.code == 404:
            return {"reachable": True, "versions": set(), "latest": None}
        return {"reachable": False, "versions": set(), "latest": None}
    except OSError:
        return {"reachable": False, "versions": set(), "latest": None}
    return {
        "reachable": True,
        "versions": set(data.get("releases", {})),
        # The latest *stable* release: what an unpinned `pip install` resolves to, and so
        # what a new release has to exceed.
        "latest": data.get("info", {}).get("version"),
    }


# Enough PEP 440 for this lane: a release segment plus an optional dev/pre/post suffix,
# so 3.0.0rc1 sorts below 3.0.0 and 3.0.0.post1 above it.
_VERSION_RE = re.compile(
    r"""^\s*v?
    (?P<release>\d+(?:\.\d+)*)
    (?:[-_.]?(?P<pre>a|b|c|rc|alpha|beta|pre|preview)[-_.]?(?P<pre_n>\d+)?)?
    (?:[-_.]?(?P<post>post|rev|r)[-_.]?(?P<post_n>\d+)?)?
    (?:[-_.]?dev[-_.]?(?P<dev_n>\d+)?)?
    (?:\+(?P<local>.+))?\s*$""",
    re.IGNORECASE | re.VERBOSE,
)

# dev < pre-release < final < post-release, matching PEP 440's ordering.
_DEV, _PRE, _FINAL, _POST = 0, 1, 2, 3


def _release_key(version: str) -> tuple:
    """A sort key for a distribution version.

    An unparseable version sorts below everything, so it cannot look like an upgrade.
    """
    match = _VERSION_RE.match(version or "")
    if not match:
        return ((), _DEV, 0)
    # Padded so 1.1 and 1.1.0 compare equal rather than by tuple length.
    release = tuple(int(part) for part in match["release"].split("."))
    release = release + (0,) * (3 - len(release))
    if match["dev_n"] is not None or "dev" in (version or "").lower():
        return (release, _DEV, int(match["dev_n"] or 0))
    if match["pre"]:
        return (release, _PRE, int(match["pre_n"] or 0))
    if match["post"]:
        return (release, _POST, int(match["post_n"] or 0))
    return (release, _FINAL, 0)


def _is_newer(candidate: str, other: str) -> bool:
    """Whether `candidate` is strictly greater than `other` in PEP 440 order."""
    return _release_key(candidate) > _release_key(other)


def release_candidates() -> tuple[list[dict], list[dict]]:
    """Lane members whose declared version is ahead of the index, and those that are not.

    The only question asked of each member is "does it declare a version above the latest
    one PyPI serves?". Nothing here looks at git: which commit did the bump, and how long
    ago, has no bearing on whether consumers are missing that version.

    Consequences worth naming:

    - a bump that landed weeks ago is still a candidate until it is actually published,
      so a missed release repairs itself on the next run rather than staying missed.
    - re-runs are idempotent for free — the second run sees the version on the index.
    - a member trailing the index (`ghga-validator` declares 1.1.1 while PyPI serves
      1.2.0, because upstream kept releasing) is *skipped*, not an error. It is behind,
      which is a sync question, not a release one.
    """
    candidates, skipped = [], []
    for member in pypi_members():
        version = member["version"]
        project = _pypi_project(member["package"])
        if not project["reachable"]:
            # "Could not tell" must not read as "nothing to do" — release_plan errors.
            candidates.append(dict(member, pypi_latest=None, index_unreachable=True))
            continue
        member = dict(member, pypi_latest=project["latest"], index_unreachable=False)
        latest = project["latest"]
        if not version:
            skipped.append(dict(member, reason="declares no version"))
        elif version in project["versions"]:
            # Catches the case `latest` cannot: a prerelease is on the index but is not
            # the latest *stable*, so the comparison below would re-select it forever.
            skipped.append(dict(member, reason=f"{version} is already on the index"))
        elif latest and not _is_newer(version, latest):
            skipped.append(
                dict(member, reason=f"{version} is not above the released {latest}")
            )
        else:
            candidates.append(member)
    return candidates, skipped


def _publish_order(members: list[dict]) -> list[dict]:
    """The release set, dependencies first.

    Uploading a dependent before its dependency leaves a window where the tool is on the
    index and the version it needs is not. Closure depth gives the order; the set is at
    most three members, so nothing cleverer is needed.
    """
    by_path = {member["path"]: member for member in members}
    return sorted(
        members,
        key=lambda member: (
            len([d for d in member["internal_deps"] if d in by_path]),
            member["path"],
        ),
    )


def release_plan() -> dict:
    """What to publish, in what order, and why it may not be publishable at all.

    The set is every lane member the index is behind on; the order is dependencies
    first, so a tool never reaches PyPI before the library version it needs.

    A dependency that changed *without* a bump is deliberately not a problem. It is not
    a candidate, so the dependant resolves it from the index like any consumer would —
    for the outside world that library did not change, and holding an unrelated release
    hostage to someone's unreleased work would be wrong. What keeps that honest is the
    published-combo matrix: it resolves the same way, so the combination under test is
    the combination that ships. If the dependant genuinely needs unreleased code, its
    own floor says so and the install fails there, which is the accurate signal.

    Errors are hard — half a train on the index is worse than none:

    - an internal dependency is outside the lane: nobody could install it.
    - PyPI was unreachable, so the whole question could not be answered. "Could not
      tell" must not read as "nothing to do".
    """
    candidates, skipped = release_candidates()
    unreachable = [m for m in candidates if m["index_unreachable"]]
    publishing = [m for m in candidates if not m["index_unreachable"]]
    release_members = {member["path"] for member in publishing}
    lane_paths = {member["path"] for member in pypi_members()}
    errors = []

    for member in unreachable:
        errors.append(
            f"{member['package']}: could not reach PyPI to establish what is already"
            f" released — refusing to plan a release against an unknown index"
        )

    for member in publishing:
        for dep in member["internal_deps"]:
            if dep not in lane_paths:
                errors.append(
                    f"{member['package']}: internal dependency {dep} is not in the PyPI"
                    " lane, so consumers could never install it"
                )

    # Re-read now that the release set is known, so each member carries the closure that
    # will be built from the repo rather than resolved from the index.
    by_path = {m["path"]: m for m in pypi_members(release_members=release_members)}
    ordered = _publish_order(
        [dict(m, train_deps=by_path[m["path"]]["train_deps"]) for m in publishing]
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--paths", nargs="*", help="restrict to these member paths (default: all)"
    )
    parser.add_argument(
        "--members", action="store_true", help="emit lane members instead of cells"
    )
    parser.add_argument(
        "--dev-requirements",
        action="store_true",
        help="print the test dependencies, one per line",
    )
    parser.add_argument(
        "--candidates",
        action="store_true",
        help="emit members whose declared version is ahead of the index",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="emit the release plan: ordered members, paths, skips and errors",
    )
    parser.add_argument(
        "--check-pypi",
        action="store_true",
        help="ask the index which members are being released, so cells build that"
        " closure from the repo instead of resolving it from PyPI",
    )
    args = parser.parse_args(argv)

    if args.dev_requirements:
        print("\n".join(dev_requirements()))
        return 0
    if args.plan:
        print(json.dumps(release_plan()))
        return 0
    if args.candidates:
        candidates, _ = release_candidates()
        # No errors channel here, so an unanswerable index is an exit code instead.
        if any(member["index_unreachable"] for member in candidates):
            sys.exit(
                "error: could not reach PyPI to establish what is already released"
            )
        print(json.dumps(candidates))
        return 0

    release_members = set()
    if args.check_pypi:
        candidates, _ = release_candidates()
        if any(member["index_unreachable"] for member in candidates):
            sys.exit(
                "error: could not reach PyPI to establish what is already released"
            )
        release_members = {member["path"] for member in candidates}

    members = pypi_members(args.paths, release_members=release_members)
    print(json.dumps(members if args.members else matrix_cells(members)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
