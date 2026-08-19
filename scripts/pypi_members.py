#!/usr/bin/env python3
"""Enumerate the PyPI-lane workspace members and the published-combo test matrix.

Single source of truth for pypi-matrix.yaml and pypi-publish.yaml; image_members.py is the
platform-lane counterpart. Lane membership follows ADR-0014: libs/* defaults to pypi,
tools/* to none, services/* to platform, each overridable with [tool.ghga] release.

The Python range lives in TEST_PYTHONS here, not in the members' requires-python: those
files are synced one-way from upstream and conflict if edited. It is intersected with what
each member declares, so the matrix widens by itself once the declarations improve.

Usage:
    python scripts/pypi_members.py                      # test matrix cells (json)
    python scripts/pypi_members.py --members            # lane members only
    python scripts/pypi_members.py --paths libs/hexkit  # restrict to given members
    python scripts/pypi_members.py --dev-requirements --package hexkit  # test deps
    python scripts/pypi_members.py --bumped --base HEAD^  # members whose version moved
    python scripts/pypi_members.py --plan --base HEAD^    # ordered release plan + errors

stdlib only (python >= 3.11 for tomllib).
"""

from __future__ import annotations

import argparse
import functools
import json
import pathlib
import re
import subprocess
import sys

import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]

# The same dependency graph the affected-target matrix uses, so the two cannot disagree.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from affected_targets import internal_dep_graph

# The versions the matrix runs on. 3.13 (the workspace's own) is deferred for now; nothing
# in the repo runs 3.14 yet.
TEST_PYTHONS = ("3.11", "3.12")

# Directory defaults for the release lane (ADR-0014).
LANE_DEFAULTS = {"libs": "pypi", "tools": "none", "services": "platform"}

# Members testable on fewer versions than they declare. schemapack says >=3.12, but its
# suite needs the schema-comparison extra, which needs 3.13. Drop when that floor drops.
EFFECTIVE_REQUIRES_PYTHON = {"schemapack": ">=3.13"}

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


def pypi_members(paths: list[str] | None = None) -> list[dict]:
    """Every workspace member released to PyPI, with its intersected Python versions."""
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
            # Follow the narrower set, so the matrix never claims an untested version.
            testable = EFFECTIVE_REQUIRES_PYTHON.get(project["name"], requires_python)
            members.append(
                {
                    "path": relative,
                    "package": project["name"],
                    "version": project.get("version", ""),
                    "requires_python": requires_python,
                    "testable_requires_python": testable,
                    "internal_deps": _closure(relative, graph),
                    "extras": _test_extras(project.get("optional-dependencies", {})),
                    "pythons": [p for p in TEST_PYTHONS if _supported(testable, p)],
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
            # Built into the same wheelhouse, so a release train resolves against the
            # libraries from this commit rather than the older ones on PyPI.
            "internal_deps": " ".join(member["internal_deps"]),
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


def _version_at(ref: str, path: str) -> str | None:
    """A member's declared version at a git ref, or None if it did not exist there.

    Only meaningful for a ref that resolves: git exits non-zero both for a path missing
    from a real commit and for an unknown revision, so against a bad ref every member
    reads as newly added. Callers resolve the base with _resolve_ref first.
    """
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}/pyproject.toml"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    try:
        return tomllib.loads(result.stdout)["project"].get("version")
    except (tomllib.TOMLDecodeError, KeyError):
        return None


def _resolve_ref(ref: str) -> str | None:
    """The commit `ref` names, or None if it names none in this clone.

    `--verify` demands one unambiguous object, `^{commit}` rejects blobs and trees and
    peels an annotated release tag to its commit, `--quiet` turns the failure into a
    plain exit code. Resolving once also pins the comparison, so a ref that moves cannot
    shift under a running plan.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or None


def _unresolvable_base(base: str) -> str:
    """Why a plan against `base` is refused instead of attempted."""
    return (
        f"base ref {base!r} does not name a commit in this clone — refusing to plan a"
        " release against a comparison that cannot be made. A shallow checkout (no"
        " HEAD^), an unfetched tag, and a push event's all-zero `before` SHA all land"
        " here; unguarded, every member reads as newly added and every closure-train"
        " check passes silently"
    )


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


def _on_pypi(package: str, version: str) -> bool:
    """Whether this version is already on PyPI — the duplicate-upload guard.

    Bumps arrive through the mainline sync while upstream still publishes, so a bumped
    version usually means a release that already happened there. An unreachable index
    counts as published; release_plan errors on that separately, so it cannot pass for
    "nothing to do".
    """
    project = _pypi_project(package)
    return version in project["versions"] if project["reachable"] else True


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


def bumped_members(base: str, check_pypi: bool) -> list[dict]:
    """Lane members whose declared version moved since `base` and is not yet published.

    `base` is a commit the caller has already resolved (_resolve_ref); the version
    lookup cannot tell an unresolvable ref from a member that did not exist yet.
    """
    candidates = []
    for member in pypi_members():
        previous = _version_at(base, member["path"])
        current = member["version"]
        if not current or current == previous:
            continue
        member = dict(member, previous_version=previous)
        member["already_published"] = (
            _on_pypi(member["package"], current) if check_pypi else False
        )
        project = _pypi_project(member["package"]) if check_pypi else None
        # For release_plan's ordering check. None = never published, or not reachable.
        member["pypi_latest"] = project["latest"] if project else None
        # "Could not tell" must not read as "up to date" — release_plan errors on it.
        member["index_unreachable"] = bool(project and not project["reachable"])
        candidates.append(member)
    return candidates


def _changed_since(base: str, path: str) -> bool:
    """Whether anything under `path` changed since `base`.

    `base` must be resolved for the same reason: a diff that failed to run is
    indistinguishable here from one that found nothing.
    """
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD", "--", path],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


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


def release_plan(base: str, check_pypi: bool) -> dict:
    """What to publish, in what order, and why it may not be publishable at all.

    Every error is hard — half a train on the index is worse than none:

    - an internal dependency changed since `base` but was not bumped: the tool would be
      published against code it was never tested with (ADR-0004's closure train).
    - an internal dependency is outside the lane: nobody could install it.
    - the version did not move forwards, or is below what PyPI already serves. A version
      that merely *differs* is not a release — the sync moves them sideways, and members
      can trail upstream (ghga-validator does today).
    - PyPI was unreachable, so "already published" could not be established.
    - `base` does not resolve, so no comparison could be made at all. Same rule as the
      line above, applied to git: "could not tell" must not read as an answer.

    ADR-0004 also asks the closure to be pinned exactly; deliberately not done, since it
    means editing synced pyprojects and stops users taking dependency fixes. The
    published-combo matrix covers that instead, by testing the real resolution.
    """
    # Before anything reads history: an empty plan with one error, not a plan built on a
    # comparison that never happened. Messages below still quote `base` as given, since
    # "since HEAD^" reads better than a bare sha.
    resolved = _resolve_ref(base)
    if resolved is None:
        return {"members": [], "paths": [], "errors": [_unresolvable_base(base)]}

    candidates = bumped_members(resolved, check_pypi)
    bumped = [m for m in candidates if not m["already_published"]]
    publishing = {member["path"] for member in bumped}
    lane_paths = {member["path"] for member in pypi_members()}
    errors = []

    # Over every candidate, not just the unpublished ones: an unreachable index marks them
    # all published, draining the plan to a silent "nothing to do".
    for member in candidates:
        if member["index_unreachable"]:
            errors.append(
                f"{member['package']}: could not reach PyPI to check whether"
                f" {member['version']} is already published — refusing to plan a release"
                " against an unknown index"
            )

    for member in bumped:
        previous = member["previous_version"]
        if previous and not _is_newer(member["version"], previous):
            errors.append(
                f"{member['package']}: version went {previous} -> {member['version']}"
                f" since {base}, which is not an increase — a release must move the"
                " series forwards"
            )
        latest = member["pypi_latest"]
        if latest and not _is_newer(member["version"], latest):
            errors.append(
                f"{member['package']}: {member['version']} is not above {latest}, the"
                " latest release already on PyPI — publishing it would put an older"
                " artifact on the index than the one consumers resolve to"
            )

        for dep in member["internal_deps"]:
            if dep not in lane_paths:
                errors.append(
                    f"{member['package']}: internal dependency {dep} is not in the PyPI"
                    " lane, so consumers could never install it"
                )
            elif dep not in publishing and _changed_since(resolved, dep):
                errors.append(
                    f"{member['package']}: internal dependency {dep} changed since"
                    f" {base} but was not bumped — release it from this commit too,"
                    " or the published tool resolves against code it was not tested with"
                )

    ordered = _publish_order(bumped)
    return {
        "members": ordered,
        "paths": [member["path"] for member in ordered],
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
        "--bumped", action="store_true", help="emit members whose version moved"
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="emit the release plan: ordered members, paths, and closure-train errors",
    )
    parser.add_argument("--base", default="HEAD^", help="base ref for --bumped/--plan")
    parser.add_argument(
        "--check-pypi",
        action="store_true",
        help="with --bumped/--plan: skip versions that already exist on PyPI",
    )
    args = parser.parse_args(argv)

    if args.dev_requirements:
        print("\n".join(dev_requirements(args.package)))
        return 0
    if args.plan:
        print(json.dumps(release_plan(args.base, args.check_pypi)))
        return 0
    if args.bumped:
        # No errors channel here, so the refusal is an exit code on stderr instead.
        resolved = _resolve_ref(args.base)
        if resolved is None:
            sys.exit(f"error: {_unresolvable_base(args.base)}")
        print(json.dumps(bumped_members(resolved, args.check_pypi)))
        return 0

    members = pypi_members(args.paths)
    print(json.dumps(members if args.members else matrix_cells(members)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
