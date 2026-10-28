#!/usr/bin/env python3
"""Compare Trivy or uv audit JSON reports and render the outcome as markdown.

Used by .github/workflows/security-scan.yaml in three modes:

  diff      two reports of one kind (before/after a lockfile update) into a
            "fragment": the vulnerabilities the update fixed and the ones it
            introduced. Records are paired by package and advisory, the same
            version first, so a version bump of a still-vulnerable package does
            not count as a fix.
  render    one or more fragments into a markdown report (the PR body / job
            summary) and print the number of fixed DEPENDENCY vulnerabilities to
            stdout, which the workflow uses as its open-a-PR gate.
  exposure  one uv audit report into the job summary's current-exposure tables.

Fixed vulnerabilities are split by origin. OS packages live in the base image, out
of reach of any lockfile, and dev-only packages never ship, so their fixes are
reported but never gate a PR. Only fixes in runtime dependencies do.
"""

import argparse
import json
import pathlib
import re
from typing import Any

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}

# Trivy's Result.Class for OS packages. Anything else these scans produce is
# lang-pkgs, i.e. a dependency the lockfiles control.
OS_PKGS = "os-pkgs"
LANG_PKGS = "lang-pkgs"

# Class of a uv audit finding in a package the published images do not install,
# one that only a dependency group or an extra brings in.
DEV_ONLY = "dev-only"

# The ecosystem of every uv audit record, and of a Trivy record whose Result.Type
# is one of PYTHON_TYPES. Any other Trivy type is an ecosystem of its own.
PYPI = "pypi"
PYTHON_TYPES = {"python-pkg", "pip", "pipenv", "poetry", "uv"}


def _read_json(path):
    return json.loads(pathlib.Path(path).read_text())


def _normalize(name):
    """Normalize a distribution name as PEP 503 does, so both scanners' names match."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _name(record):
    """The package name records are matched on; PEP 503 applies to PyPI only."""
    package = record["package"]
    return _normalize(package) if record["ecosystem"] == PYPI else package


def _ids(record):
    return {record["id"], *record.get("aliases", [])}


def _same_advisory(a, b):
    return (
        a["ecosystem"] == b["ecosystem"]
        and _name(a) == _name(b)
        and bool(_ids(a) & _ids(b))
    )


def _group(records, by_version):
    """Partition records into advisories, as lists in first-seen order.

    Records of one package whose IDs or aliases overlap, directly or through another
    record, are one advisory: OSV returns one under its GHSA and its PYSEC ID, and
    Trivy names it by its CVE. With `by_version`, each installed version of a
    package is a group of its own.
    """
    records = list(records)
    parent = list(range(len(records)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    owner: dict[tuple[str, ...], int] = {}
    for i, r in enumerate(records):
        package = (r["ecosystem"], _name(r), r["installed"] if by_version else "")
        for vuln_id in _ids(r):
            parent[find(i)] = find(owner.setdefault((*package, vuln_id), i))
    groups: dict[int, list[dict[str, Any]]] = {}
    for i, r in enumerate(records):
        groups.setdefault(find(i), []).append(r)
    return list(groups.values())


def _merge(records):
    """Collapse each advisory into its first record, carrying the others' IDs as aliases."""
    merged = []
    for first, *rest in _group(records, by_version=True):
        ids = dict.fromkeys(i for r in (first, *rest) for i in sorted(_ids(r)))
        fixed_in = dict.fromkeys(
            v for r in (first, *rest) for v in r["fixed_in"].split(", ") if v
        )
        merged.append(
            {
                **first,
                "aliases": [i for i in ids if i != first["id"]],
                "fixed_in": ", ".join(fixed_in),
            }
        )
    return merged


def _load_trivy(path):
    """Flatten a Trivy JSON report into one record per vulnerability and package.

    Results (per-target sections) are merged: the mono image reports the OS
    packages and the Python venv separately, but for fixed/introduced
    accounting only the vulnerability and the package matter. Each record
    keeps its section's Class, which separates base-image from dependency
    findings. VendorIDs are not aliases: one distribution advisory (a DSA, say)
    fixes several CVEs, and taking it as an alias would merge them.
    """
    vulns: dict[tuple[str, str, str], dict[str, Any]] = {}
    for result in _read_json(path).get("Results") or []:
        result_type = result.get("Type", "")
        for v in result.get("Vulnerabilities") or []:
            key = (
                v["VulnerabilityID"],
                v.get("PkgName", ""),
                v.get("InstalledVersion", ""),
            )
            vulns.setdefault(
                key,
                {
                    "id": v["VulnerabilityID"],
                    "aliases": [],
                    "ecosystem": PYPI if result_type in PYTHON_TYPES else result_type,
                    "package": v.get("PkgName", ""),
                    "installed": v.get("InstalledVersion", ""),
                    "fixed_in": v.get("FixedVersion", ""),
                    "severity": v.get("Severity") or "UNKNOWN",
                    "url": v.get("PrimaryURL", ""),
                    "class": result.get("Class", ""),
                },
            )
    return list(vulns.values())


def _load_runtime(path):
    """Read the (name, version) pairs from a `uv export` requirements file.

    A line whose environment marker does not hold for this interpreter is left out,
    so the workflow runs this on the Linux CPython version the images ship. A line
    without an exact pin, a URL dependency, counts for every version, as None.
    """
    # Imported here: only uv-audit modes need it, and the PR job runs bare python3.
    from packaging.requirements import Requirement

    pairs = set()
    for line in pathlib.Path(path).read_text().splitlines():
        if not re.match(r"[A-Za-z0-9]", line):
            continue
        requirement = Requirement(line)
        if requirement.marker is not None and not requirement.marker.evaluate():
            continue
        pins = [s.version for s in requirement.specifier if s.operator == "=="]
        pairs.add((_normalize(requirement.name), pins[0] if len(pins) == 1 else None))
    return pairs


def _load_uv_audit(report, runtime):
    """Flatten a parsed uv audit report into one record per advisory and package version.

    uv audit reports no severity. A package version missing from `runtime`, the
    (name, version) pairs the published images install, is classed DEV_ONLY.
    """
    vulns: dict[tuple[str, str, str], dict[str, Any]] = {}
    for v in report.get("vulnerabilities") or []:
        package = v["dependency"]["name"]
        version = v["dependency"].get("version", "")
        installed = runtime & {
            (_normalize(package), version),
            (_normalize(package), None),
        }
        vulns.setdefault(
            (v["id"], package, version),
            {
                "id": v["id"],
                "aliases": v.get("aliases") or [],
                "ecosystem": PYPI,
                "package": package,
                "installed": version,
                "fixed_in": ", ".join(v.get("fix_versions") or []),
                "severity": "",
                "url": v.get("link") or "",
                "class": LANG_PKGS if installed else DEV_ONLY,
            },
        )
    return _merge(vulns.values())


def _adverse(report):
    """Describe each adverse status of a parsed uv audit report in one line.

    The entries' shape is not documented yet, so a package is named where the
    entry has one and the entry is shown as it is.
    """
    lines = []
    for status in report.get("adverse_statuses") or []:
        dependency = status.get("dependency") if isinstance(status, dict) else None
        if isinstance(dependency, dict) and dependency.get("name"):
            rest = {k: v for k, v in status.items() if k != "dependency"}
            lines.append(
                f"`{dependency['name']}` {dependency.get('version', '')}: "
                f"{json.dumps(rest)}"
            )
        else:
            lines.append(json.dumps(status))
    return lines


def _pair(before, after):
    """Pair each record with one of the same advisory, the same version first.

    Returns the unpaired records of each side: those of `before` were fixed, those
    of `after` were introduced. Pairing across versions keeps a bump that is still
    vulnerable from counting as a fix; pairing the same version first keeps one of
    two installed versions that the update did fix from hiding behind the other.
    """
    left_before, left_after = list(before), list(after)
    for same_version in (True, False):
        unpaired = []
        for r in left_before:
            match = next(
                (
                    o
                    for o in left_after
                    if _same_advisory(r, o)
                    and (not same_version or o["installed"] == r["installed"])
                ),
                None,
            )
            if match is None:
                unpaired.append(r)
            else:
                left_after.remove(match)
        left_before = unpaired
    return left_before, left_after


def _by_severity(records):
    return sorted(
        records,
        key=lambda r: (
            SEVERITY_ORDER.get(r["severity"], 5),
            r["id"],
            r["package"],
            r["installed"],
        ),
    )


def _diff(args):
    adverse: list[str] = []
    if args.format == "uv-audit":
        runtime = _load_runtime(args.runtime)
        after_report = _read_json(args.after)
        before = _load_uv_audit(_read_json(args.before), runtime)
        after = _load_uv_audit(after_report, runtime)
        adverse = _adverse(after_report)
    else:
        before = _load_trivy(args.before)
        after = _load_trivy(args.after)
    fixed, introduced = _pair(before, after)
    fragment = {
        "label": args.label,
        "before_count": len(before),
        "after_count": len(after),
        "fixed": _by_severity(fixed),
        "introduced": _by_severity(introduced),
        "adverse": adverse,
    }
    pathlib.Path(args.out).write_text(json.dumps(fragment, indent=2) + "\n")


def _table(records):
    lines = [
        "| Vulnerability | Severity | Package | Installed | Fixed in |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in records:
        ref = f"[{r['id']}]({r['url']})" if r["url"] else r["id"]
        lines.append(
            f"| {ref} | {r['severity'] or '-'} | `{r['package']}` "
            f"| {r['installed']} | {r['fixed_in'] or '-'} |"
        )
    return lines


def _split_by_origin(records):
    """Partition records into the runtime dependency, dev-only and base-image ones."""
    deps: list[dict[str, Any]] = []
    dev: list[dict[str, Any]] = []
    base: list[dict[str, Any]] = []
    for r in records:
        {OS_PKGS: base, DEV_ONLY: dev}.get(r.get("class"), deps).append(r)
    return deps, dev, base


def _list_once(record_lists):
    """Drop from each list the PyPI advisories an earlier list holds; count all of them.

    Trivy and uv audit both see the Python runtime dependencies, so a fix both
    report is listed and counted once, in the first fragment that has it. Records
    of any other ecosystem stay: two images that share a base package each carry
    its fix or regression.
    """
    record_lists = [list(records) for records in record_lists]
    pypi = (r for records in record_lists for r in records if r["ecosystem"] == PYPI)
    group_of: dict[int, object] = {
        id(r): (PYPI, n)
        for n, members in enumerate(_group(pypi, by_version=False))
        for r in members
    }
    first: dict[object, int] = {}
    kept = [
        [r for r in records if first.setdefault(group_of.get(id(r), id(r)), n) == n]
        for n, records in enumerate(record_lists)
    ]
    return kept, len(first)


def _section(heading, records, listed_above=0):
    lines = [f"**{heading} ({len(records)}):**", ""]
    lines.extend(_table(records) if records else ["none"])
    if listed_above:
        lines.extend(
            ["", f"{listed_above} more already listed above, under another ID."]
        )
    lines.append("")
    return lines


def _collapsed_section(heading, records):
    """Render a section folded away, for a long list that never gates a PR."""
    summary = f"<summary>{heading} ({len(records)})</summary>"
    return ["<details>", summary, "", *_table(records), "", "</details>", ""]


def _adverse_section(heading, lines):
    return [f"**{heading} ({len(lines)}):**", "", *(f"- {line}" for line in lines), ""]


def _render_fragment(fragment, fixed_deps, introduced):
    """Render a fragment, with its fixed dependency and introduced records deduplicated."""
    lines = [
        f"### {fragment['label']}",
        "",
        f"{fragment['before_count']} known vulnerabilities before, "
        f"{fragment['after_count']} after.",
        "",
    ]
    all_fixed_deps, fixed_dev, fixed_base = _split_by_origin(fragment["fixed"])
    lines.extend(
        _section(
            "Fixed by the dependency update",
            fixed_deps,
            len(all_fixed_deps) - len(fixed_deps),
        )
    )
    if fixed_dev:
        lines.extend(
            _collapsed_section(
                "Fixed in dev-only packages, not counted toward a PR", fixed_dev
            )
        )
    if fixed_base:
        lines.extend(
            _section(
                "Fixed by the refreshed base image, not by this update", fixed_base
            )
        )
    if fragment["introduced"]:
        lines.extend(
            _section(
                "Introduced", introduced, len(fragment["introduced"]) - len(introduced)
            )
        )
    if fragment.get("adverse"):
        lines.extend(
            _adverse_section("Adverse statuses after the update", fragment["adverse"])
        )
    return lines


def _render(args):
    fragments = [_read_json(p) for p in args.fragments]
    fixed_deps, fixed_count = _list_once(
        _split_by_origin(f["fixed"])[0] for f in fragments
    )
    introduced, _ = _list_once(f["introduced"] for f in fragments)
    lines = []
    for parts in zip(fragments, fixed_deps, introduced, strict=True):
        lines.extend(_render_fragment(*parts))
    pathlib.Path(args.out).write_text("\n".join(lines).rstrip() + "\n")
    print(fixed_count)


def _exposure(args):
    report = _read_json(args.report)
    deps, dev, _ = _split_by_origin(
        _by_severity(_load_uv_audit(report, _load_runtime(args.runtime)))
    )
    packages = (report.get("summary") or {}).get("audited_packages", "?")
    lines = [
        f"{len(deps) + len(dev)} known vulnerabilities in {packages} packages.",
        "",
        *_section("In packages the images install", deps),
    ]
    if dev:
        lines.extend(_collapsed_section("In dev-only packages", dev))
    if adverse := _adverse(report):
        lines.extend(_adverse_section("Adverse statuses", adverse))
    pathlib.Path(args.out).write_text("\n".join(lines).rstrip() + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    diff = sub.add_parser("diff", help="diff two JSON reports into a fragment")
    diff.add_argument("--label", required=True, help="artifact name shown in reports")
    diff.add_argument(
        "--format", choices=["trivy", "uv-audit"], default="trivy", help="report kind"
    )
    diff.add_argument("--before", required=True, help="JSON report (before)")
    diff.add_argument("--after", required=True, help="JSON report (after)")
    diff.add_argument(
        "--runtime",
        help="uv export of the packages the images install (required for uv-audit)",
    )
    diff.add_argument("--out", required=True, help="fragment JSON output path")
    diff.set_defaults(func=_diff)
    render = sub.add_parser("render", help="render fragments to markdown")
    render.add_argument("fragments", nargs="+", help="fragment JSON files")
    render.add_argument("--out", required=True, help="markdown output path")
    render.set_defaults(func=_render)
    exposure = sub.add_parser("exposure", help="render one uv audit report to markdown")
    exposure.add_argument("--report", required=True, help="uv audit JSON report")
    exposure.add_argument(
        "--runtime", required=True, help="uv export of the packages the images install"
    )
    exposure.add_argument("--out", required=True, help="markdown output path")
    exposure.set_defaults(func=_exposure)
    args = parser.parse_args()
    if args.mode == "diff" and args.format == "uv-audit" and not args.runtime:
        parser.error("--format uv-audit requires --runtime")
    args.func(args)


if __name__ == "__main__":
    main()
