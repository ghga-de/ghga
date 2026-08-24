#!/usr/bin/env python3
"""Enumerate the PyPI-lane workspace members and the published-combo test matrix.

Single source of truth for pypi-matrix.yaml and pypi-publish.yaml; image_members.py is the
platform-lane counterpart. Lane membership follows ADR-0014: libs/* defaults to pypi,
tools/* to none, services/* to platform, each overridable with [tool.ghga] release.

What needs releasing is decided against the *index*, never against git history: a member
is a release candidate when the version it declares is above the latest one on PyPI. A
version bump is the release trigger, so it does not matter which commit made it, how long
ago, or whether it arrived through the mainline sync — only whether the index has caught
up. Diffing two refs would answer a different question ("did this commit bump it?") and
silently miss a bump that landed earlier.

Usage:
    python scripts/pypi_members.py --check-pypi         # test matrix cells (json)
    python scripts/pypi_members.py --members            # lane members only
    python scripts/pypi_members.py --paths libs/hexkit  # restrict to given members
    python scripts/pypi_members.py --dev-requirements --package hexkit  # test deps
    python scripts/pypi_members.py --candidates         # members whose version is unreleased
    python scripts/pypi_members.py --plan               # ordered release plan + errors

stdlib only (python >= 3.11 for tomllib).
"""

from __future__ import annotations

import argparse
import functools
import json
import pathlib
import re
import sys

import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]

# The same dependency graph the affected-target matrix uses, so the two cannot disagree.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from affected_targets import internal_dep_graph

# The versions the matrix runs on.
TEST_PYTHONS = ("3.11", "3.12", "3.13", "3.14")

# Directory defaults for the release lane (ADR-0014).
LANE_DEFAULTS = {"libs": "pypi", "tools": "none", "services": "platform"}

# Lint/type tools in the root dev group. A cell only runs tests, and one of these failing
# to resolve on an older Python would fail it for an unrelated reason.
NON_TEST_TOOLS = ("ruff", "mypy", "pre-commit")

# Test imports a member declares nowhere and the root dev group does not supply. The
# workspace hides them — some sibling drags the distribution into the shared venv. Keyed
# per member so one workaround cannot leak into another's environment. Fix upstream, then
# delete the entry.
MATRIX_ONLY_REQUIREMENTS = {
    # In hexkit's shipped s3 testutils, so consumers hit this too; belongs in `test-s3`.
    "hexkit": ("httpx2>=2.9.1,<3",),
    # connector's fixtures import ghga_service_commons.api; it requires only [crypt,transports].
    "ghga_connector": ("ghga-service-commons[api]",),
}


def _requirement_name(spec: str) -> str:
    """The distribution name at the head of a requirement specifier."""
    for i, ch in enumerate(spec):
        if ch in "<>=!~[ ;(":
            return spec[:i].strip().lower()
    return spec.strip().lower()


def _parse_version(text: str) -> tuple[int, ...]:
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
            # ~=X.Y  ->  >=X.Y and <(X+1);  ~=X.Y.Z  ->  >=X.Y.Z and <X.(Y+1)
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
    """Every extra a member declares — its own suite may need any of them.

    Not just `all`: hexkit's omits redis, so an `all` install cannot collect those tests.
    """
    return sorted(optional)


def _closure(path: str, graph: dict[str, set[str]]) -> list[str]:
    """Every workspace member `path` depends on, transitively — its closure train."""
    seen: set[str] = set()
    queue = list(graph.get(path, ()))
    while queue:
        dep = queue.pop()
        if dep in seen:
            continue
        seen.add(dep)
        queue.extend(graph.get(dep, ()))
    return sorted(seen)


def _lane(root: str, ghga: dict) -> str:
    lane = ghga.get("release")
    if lane:
        return lane
    if ghga.get("pypi"):
        return "pypi"
    return LANE_DEFAULTS.get(root, "none")


def pypi_members(
    paths: list[str] | None = None, train: set[str] | None = None
) -> list[dict]:
    """Every workspace member released to PyPI, with its intersected Python versions.

    `train` is the set of member paths being released in this same run. It splits each
    member's closure in two: `train_deps` are built from the repo, because the versions
    they declare are not on the index yet; everything else is left to resolve from PyPI,
    which is what a consumer's install does. Without a train nothing is built locally —
    the safe default, since resolving from the index can only under-state what is
    available, never over-state it.
    """
    graph = internal_dep_graph()
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
            if paths and relative not in paths:
                continue
            data = tomllib.loads(manifest.read_text())
            ghga = data.get("tool", {}).get("ghga", {})
            # _lane decides alone: honouring `pypi = true` here would readmit a member
            # that `release = "none"` excluded.
            if _lane(root, ghga) != "pypi":
                continue
            project = data["project"]
            requires_python = project.get("requires-python", "")
            closure = _closure(relative, graph)
            members.append(
                {
                    "path": relative,
                    "package": project["name"],
                    "version": project.get("version", ""),
                    "requires_python": requires_python,
                    "internal_deps": closure,
                    "train_deps": sorted(d for d in closure if d in (train or ())),
                    "extras": _test_extras(project.get("optional-dependencies", {})),
                    # TEST_PYTHONS is intersected with what each member declares in its
                    # own requires-python, so a member is
                    # never claimed to be tested on a version it does not support.
                    "pythons": [
                        p for p in TEST_PYTHONS if _supported(requires_python, p)
                    ],
                }
            )
    return members


def matrix_cells(members: list[dict]) -> list[dict]:
    """One entry per (member, python version) — the shape a GitHub matrix consumes."""
    return [
        {
            "path": member["path"],
            "package": member["package"],
            "extras": ",".join(member["extras"]),
            # Only the closure being released alongside this member goes into the
            # wheelhouse. Its other dependencies resolve from the index, so the cell
            # installs the combination a consumer gets rather than one only this
            # checkout can produce.
            "train_deps": " ".join(member["train_deps"]),
            "python": python,
        }
        for member in members
        for python in member["pythons"]
    ]


def dev_requirements(package: str | None = None) -> list[str]:
    """What a bare environment needs to run a member's suite.

    The root dev group minus lint/type tooling, plus that member's undeclared test
    imports (NON_TEST_TOOLS, MATRIX_ONLY_REQUIREMENTS).
    """
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    group = data.get("dependency-groups", {}).get("dev", [])
    shared = [
        spec
        for spec in group
        if isinstance(spec, str) and _requirement_name(spec) not in NON_TEST_TOOLS
    ]
    return shared + list(MATRIX_ONLY_REQUIREMENTS.get(package or "", ()))


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
    train = {member["path"] for member in publishing}
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

    # Re-read with the train known, so each member carries the closure that will be built
    # from the repo rather than resolved from the index.
    by_path = {m["path"]: m for m in pypi_members(train=train)}
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
        "--package",
        help="with --dev-requirements: add that member's undeclared test imports",
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
        print("\n".join(dev_requirements(args.package)))
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

    train = set()
    if args.check_pypi:
        candidates, _ = release_candidates()
        if any(member["index_unreachable"] for member in candidates):
            sys.exit(
                "error: could not reach PyPI to establish what is already released"
            )
        train = {member["path"] for member in candidates}

    members = pypi_members(args.paths, train=train)
    print(json.dumps(members if args.members else matrix_cells(members)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
