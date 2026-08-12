#!/usr/bin/env python3
"""Compare Trivy JSON reports and render the outcome as markdown.

Used by .github/workflows/security-scan.yaml in two steps:

  diff    two Trivy JSON reports (before/after a lockfile update) into a
          "fragment": the vulnerabilities the update fixed and the ones it
          introduced, identified by (VulnerabilityID, PkgName) so version
          bumps of a still-vulnerable package do not count as a fix.
  render  one or more fragments into a markdown report (the PR body / job
          summary) and print the total number of fixed vulnerabilities to
          stdout, which the workflow uses as its open-a-PR gate.
"""

import argparse
import json
import pathlib

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}


def _load_vulns(path):
    """Flatten a Trivy JSON report into {(vuln_id, package): record}.

    Results (per-target sections) are merged: the mono image reports the OS
    packages and the Python venv separately, but for fixed/introduced
    accounting only the (vulnerability, package) pair matters.
    """
    report = json.loads(pathlib.Path(path).read_text())
    vulns = {}
    for result in report.get("Results") or []:
        for v in result.get("Vulnerabilities") or []:
            key = (v["VulnerabilityID"], v.get("PkgName", ""))
            vulns.setdefault(
                key,
                {
                    "id": v["VulnerabilityID"],
                    "package": v.get("PkgName", ""),
                    "installed": v.get("InstalledVersion", ""),
                    "fixed_in": v.get("FixedVersion", ""),
                    "severity": v.get("Severity") or "UNKNOWN",
                    "url": v.get("PrimaryURL", ""),
                },
            )
    return vulns


def _by_severity(records):
    return sorted(
        records,
        key=lambda r: (SEVERITY_ORDER.get(r["severity"], 5), r["id"], r["package"]),
    )


def _diff(args):
    before = _load_vulns(args.before)
    after = _load_vulns(args.after)
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
            f"| {ref} | {r['severity']} | `{r['package']}` "
            f"| {r['installed']} | {r['fixed_in'] or '-'} |"
        )
    return lines


def _render_fragment(fragment):
    lines = [
        f"### {fragment['label']}",
        "",
        f"{fragment['before_count']} known vulnerabilities before, "
        f"{fragment['after_count']} after.",
        "",
    ]
    for kind in ("fixed", "introduced"):
        records = fragment[kind]
        if not records and kind == "introduced":
            continue
        lines.append(f"**{kind.capitalize()} ({len(records)}):**")
        lines.append("")
        lines.extend(_table(records) if records else ["none"])
        lines.append("")
    return lines


def _render(args):
    fragments = [json.loads(pathlib.Path(p).read_text()) for p in args.fragments]
    lines = []
    for fragment in fragments:
        lines.extend(_render_fragment(fragment))
    pathlib.Path(args.out).write_text("\n".join(lines).rstrip() + "\n")
    print(sum(len(f["fixed"]) for f in fragments))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    diff = sub.add_parser("diff", help="diff two Trivy JSON reports into a fragment")
    diff.add_argument("--label", required=True, help="artifact name shown in reports")
    diff.add_argument("--before", required=True, help="Trivy JSON report (before)")
    diff.add_argument("--after", required=True, help="Trivy JSON report (after)")
    diff.add_argument("--out", required=True, help="fragment JSON output path")
    diff.set_defaults(func=_diff)
    render = sub.add_parser("render", help="render fragments to markdown")
    render.add_argument("fragments", nargs="+", help="fragment JSON files")
    render.add_argument("--out", required=True, help="markdown output path")
    render.set_defaults(func=_render)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
