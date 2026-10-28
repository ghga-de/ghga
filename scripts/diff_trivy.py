#!/usr/bin/env python3
"""Compare Trivy or uv audit JSON reports and render the outcome as markdown.

Used by .github/workflows/security-scan.yaml in two steps:

  diff    two reports of one kind (before/after a lockfile update) into a
          "fragment": the vulnerabilities the update fixed and the ones it
          introduced, identified by (vulnerability ID, package) so version
          bumps of a still-vulnerable package do not count as a fix.
  render  one or more fragments into a markdown report (the PR body / job
          summary) and print the number of fixed DEPENDENCY vulnerabilities to
          stdout, which the workflow uses as its open-a-PR gate.

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


def _normalize(name):
    """Normalize a distribution name as PEP 503 does, so both scanners' names match."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _load_trivy(path):
    """Flatten a Trivy JSON report into {(vuln_id, package): record}.

    Results (per-target sections) are merged: the mono image reports the OS
    packages and the Python venv separately, but for fixed/introduced
    accounting only the (vulnerability, package) pair matters. Each record
    keeps its section's Class, which separates base-image from dependency
    findings.
    """
    report = json.loads(pathlib.Path(path).read_text())
    vulns: dict[tuple[str, str], dict[str, Any]] = {}
    for result in report.get("Results") or []:
        for v in result.get("Vulnerabilities") or []:
            key = (v["VulnerabilityID"], v.get("PkgName", ""))
            vulns.setdefault(
                key,
                {
                    "id": v["VulnerabilityID"],
                    "aliases": v.get("VendorIDs") or [],
                    "package": v.get("PkgName", ""),
                    "installed": v.get("InstalledVersion", ""),
                    "fixed_in": v.get("FixedVersion", ""),
                    "severity": v.get("Severity") or "UNKNOWN",
                    "url": v.get("PrimaryURL", ""),
                    "class": result.get("Class", ""),
                },
            )
    return vulns


def _load_runtime(path):
    """Read the distribution names from a `uv export` requirements file."""
    names = set()
    for line in pathlib.Path(path).read_text().splitlines():
        if match := re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", line):
            names.add(_normalize(match.group()))
    return names


def _load_uv_audit(path, runtime):
    """Flatten a uv audit JSON report into {(vuln_id, package): record}.

    uv audit reports no severity. A package missing from `runtime`, the names the
    published images install, is classed DEV_ONLY.
    """
    report = json.loads(pathlib.Path(path).read_text())
    vulns: dict[tuple[str, str], dict[str, Any]] = {}
    for v in report.get("vulnerabilities") or []:
        package = v["dependency"]["name"]
        vulns.setdefault(
            (v["id"], package),
            {
                "id": v["id"],
                "aliases": v.get("aliases") or [],
                "package": package,
                "installed": v["dependency"].get("version", ""),
                "fixed_in": ", ".join(v.get("fix_versions") or []),
                "severity": "",
                "url": v.get("link") or "",
                "class": LANG_PKGS if _normalize(package) in runtime else DEV_ONLY,
            },
        )
    return vulns


def _by_severity(records):
    return sorted(
        records,
        key=lambda r: (SEVERITY_ORDER.get(r["severity"], 5), r["id"], r["package"]),
    )


def _diff(args):
    if args.format == "uv-audit":
        runtime = _load_runtime(args.runtime)
        before = _load_uv_audit(args.before, runtime)
        after = _load_uv_audit(args.after, runtime)
    else:
        before = _load_trivy(args.before)
        after = _load_trivy(args.after)
    fragment = {
        "label": args.label,
        "before_count": len(before),
        "after_count": len(after),
        "fixed": _by_severity([before[k] for k in before.keys() - after.keys()]),
        "introduced": _by_severity([after[k] for k in after.keys() - before.keys()]),
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


def _count_distinct(records):
    """Count records, taking those that share a package and an ID or alias as one.

    Trivy and uv audit both see the runtime dependencies, often under different IDs
    for one advisory (a CVE against a GHSA or PYSEC ID), so a fix both report
    counts once.
    """
    groups: list[tuple[str, set[str]]] = []
    for r in records:
        package, ids = _normalize(r["package"]), {r["id"], *r.get("aliases", [])}
        for known_package, known_ids in groups:
            if known_package == package and known_ids & ids:
                known_ids |= ids
                break
        else:
            groups.append((package, ids))
    return len(groups)


def _section(heading, records):
    lines = [f"**{heading} ({len(records)}):**", ""]
    lines.extend(_table(records) if records else ["none"])
    lines.append("")
    return lines


def _collapsed_section(heading, records):
    """Render a section folded away, for a long list that never gates a PR."""
    summary = f"<summary>{heading} ({len(records)})</summary>"
    return ["<details>", summary, "", *_table(records), "", "</details>", ""]


def _render_fragment(fragment):
    lines = [
        f"### {fragment['label']}",
        "",
        f"{fragment['before_count']} known vulnerabilities before, "
        f"{fragment['after_count']} after.",
        "",
    ]
    fixed_deps, fixed_dev, fixed_base = _split_by_origin(fragment["fixed"])
    lines.extend(_section("Fixed by the dependency update", fixed_deps))
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
        lines.extend(_section("Introduced", fragment["introduced"]))
    return lines


def _render(args):
    fragments = [json.loads(pathlib.Path(p).read_text()) for p in args.fragments]
    lines = []
    for fragment in fragments:
        lines.extend(_render_fragment(fragment))
    pathlib.Path(args.out).write_text("\n".join(lines).rstrip() + "\n")
    print(
        _count_distinct(r for f in fragments for r in _split_by_origin(f["fixed"])[0])
    )


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
    args = parser.parse_args()
    if args.mode == "diff" and args.format == "uv-audit" and not args.runtime:
        parser.error("--format uv-audit requires --runtime")
    args.func(args)


if __name__ == "__main__":
    main()
