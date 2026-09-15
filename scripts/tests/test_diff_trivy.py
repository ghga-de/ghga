"""Tests for diff_trivy.py, focused on what the security scan turns into a PR.

`render`'s stdout is that gate: a lockfile update can fix a language package,
never an OS one.
"""

import json
import subprocess
import sys
from pathlib import Path

DIFF_TRIVY = Path(__file__).resolve().parents[1] / "diff_trivy.py"

SQLITE = ("os-pkgs", "CVE-2026-11822", "sqlite-libs")
SQLITE_2 = ("os-pkgs", "CVE-2026-11824", "sqlite-libs")
URLLIB3 = ("lang-pkgs", "CVE-2026-2222", "urllib3")
JINJA2 = ("lang-pkgs", "CVE-2026-3333", "jinja2")


def _write_report(path, *findings):
    """Write a Trivy JSON report holding the given (class, id, package) findings."""
    results: dict[str, list[dict]] = {}
    for result_class, vuln_id, package in findings:
        results.setdefault(result_class, []).append(
            {
                "VulnerabilityID": vuln_id,
                "PkgName": package,
                "InstalledVersion": "1.0",
                "FixedVersion": "2.0",
                "Severity": "MEDIUM",
                "PrimaryURL": f"https://example.org/{vuln_id}",
            }
        )
    report = {
        "Results": [
            {"Target": result_class, "Class": result_class, "Vulnerabilities": vulns}
            for result_class, vulns in results.items()
        ]
    }
    path.write_text(json.dumps(report))
    return path


def _run(*args):
    return subprocess.run(
        [sys.executable, str(DIFF_TRIVY), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _scan(tmp_path, before, after):
    """Diff then render as the workflow does; return its gate count and report."""
    before_path = _write_report(tmp_path / "before.json", *before)
    after_path = _write_report(tmp_path / "after.json", *after)
    fragment = tmp_path / "fragment.json"
    report = tmp_path / "report.md"
    _run(
        "diff",
        "--label",
        "test",
        "--before",
        str(before_path),
        "--after",
        str(after_path),
        "--out",
        str(fragment),
    )
    gate = _run("render", str(fragment), "--out", str(report))
    return int(gate), report.read_text()


def test_os_package_fixes_do_not_open_a_pr(tmp_path):
    """A fresh base image fixed these, so the lockfiles have nothing to offer."""
    gate, report = _scan(tmp_path, [SQLITE, SQLITE_2], [])
    assert gate == 0
    assert "**Fixed by the dependency update (0):**" in report
    assert "CVE-2026-11822" in report  # still reported, just not gating


def test_dependency_fixes_open_a_pr(tmp_path):
    gate, report = _scan(tmp_path, [URLLIB3], [])
    assert gate == 1
    assert "CVE-2026-2222" in report


def test_gate_counts_the_dependency_fixes_only(tmp_path):
    gate, report = _scan(tmp_path, [SQLITE, URLLIB3], [])
    assert gate == 1
    assert "**Fixed by the dependency update (1):**" in report
    assert "**Fixed by the refreshed base image, not by this update (1):**" in report


def test_a_still_vulnerable_package_is_no_fix(tmp_path):
    """A version bump that leaves the CVE in place must not count."""
    gate, _ = _scan(tmp_path, [URLLIB3], [URLLIB3])
    assert gate == 0


def test_regressions_are_reported(tmp_path):
    gate, report = _scan(tmp_path, [URLLIB3], [JINJA2])
    assert gate == 1
    assert "**Introduced (1):**" in report
    assert "CVE-2026-3333" in report
