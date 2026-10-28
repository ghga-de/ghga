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


# uv audit findings as (id, aliases, package); the CVE alias of PILLOW_GHSA is the
# ID Trivy reports for the same advisory.
PILLOW_GHSA = ("GHSA-aaaa-bbbb-cccc", ["CVE-2026-4444"], "pillow")
PILLOW_TRIVY = ("lang-pkgs", "CVE-2026-4444", "Pillow")
VIRTUALENV: tuple[str, list[str], str] = ("PYSEC-2026-55", [], "virtualenv")


def _write_audit(path, *findings):
    """Write a uv audit JSON report holding the given (id, aliases, package) findings."""
    vulns = [
        {
            "id": vuln_id,
            "aliases": aliases,
            "dependency": {"name": package, "version": "1.0"},
            "fix_versions": ["2.0"],
            "link": f"https://example.org/{vuln_id}",
        }
        for vuln_id, aliases, package in findings
    ]
    path.write_text(json.dumps({"vulnerabilities": vulns}))
    return path


def _write_runtime(path, runtime):
    """Write a `uv export` of the given package names, or of whole lines with a ` ; `."""
    path.write_text(
        "".join(f"{name}\n" if " ; " in name else f"{name}==1.0\n" for name in runtime)
    )
    return path


def _audit_fragment(tmp_path, before, after, runtime):
    """Diff two uv audit reports, with `runtime` as the images' package names."""
    runtime_path = _write_runtime(tmp_path / "runtime.txt", runtime)
    fragment = tmp_path / "audit-fragment.json"
    _run(
        "diff",
        "--format",
        "uv-audit",
        "--label",
        "uv.lock",
        "--before",
        str(_write_audit(tmp_path / "audit-before.json", *before)),
        "--after",
        str(_write_audit(tmp_path / "audit-after.json", *after)),
        "--runtime",
        str(runtime_path),
        "--out",
        str(fragment),
    )
    return fragment


def test_dev_only_fixes_do_not_open_a_pr(tmp_path):
    """The images never install virtualenv, so its fix is reported only."""
    fragment = _audit_fragment(tmp_path, [VIRTUALENV], [], runtime=["pillow"])
    report = tmp_path / "report.md"
    gate = _run("render", str(fragment), "--out", str(report))
    assert int(gate) == 0
    assert (
        "<summary>Fixed in dev-only packages, not counted toward a PR (1)</summary>"
        in (report.read_text())
    )


def test_runtime_fixes_from_uv_audit_open_a_pr(tmp_path):
    fragment = _audit_fragment(tmp_path, [PILLOW_GHSA], [], runtime=["Pillow"])
    report = tmp_path / "report.md"
    gate = _run("render", str(fragment), "--out", str(report))
    assert int(gate) == 1
    assert "| - | `pillow` |" in report.read_text()  # uv audit reports no severity


def test_a_fix_both_scanners_report_counts_once(tmp_path):
    """Trivy names the advisory by its CVE, uv audit by its GHSA ID."""
    audit = _audit_fragment(tmp_path, [PILLOW_GHSA], [], runtime=["pillow"])
    trivy = tmp_path / "fragment.json"
    _run(
        "diff",
        "--label",
        "image",
        "--before",
        str(_write_report(tmp_path / "before.json", PILLOW_TRIVY, URLLIB3)),
        "--after",
        str(_write_report(tmp_path / "after.json")),
        "--out",
        str(trivy),
    )
    gate = _run("render", str(trivy), str(audit), "--out", str(tmp_path / "report.md"))
    assert int(gate) == 2


def _render_audit(tmp_path, before, runtime):
    """Diff a uv audit report against a clean one and render; return gate and report."""
    fragment = _audit_fragment(tmp_path, before, [], runtime=runtime)
    report = tmp_path / "report.md"
    gate = _run("render", str(fragment), "--out", str(report))
    return int(gate), report.read_text()


def test_one_advisory_under_two_osv_ids_counts_once(tmp_path):
    """OSV returns an advisory under its GHSA and its PYSEC ID, aliasing each other."""
    gate, report = _render_audit(
        tmp_path,
        [
            ("GHSA-aaaa-bbbb-cccc", ["PYSEC-2026-1"], "pillow"),
            ("PYSEC-2026-1", ["GHSA-aaaa-bbbb-cccc"], "pillow"),
        ],
        runtime=["pillow"],
    )
    assert gate == 1
    assert "**Fixed by the dependency update (1):**" in report
    assert "1 known vulnerabilities before" in report


def test_advisories_join_through_a_later_record(tmp_path):
    """The third record links the first two, which share no ID with each other."""
    gate, _ = _render_audit(
        tmp_path,
        [
            ("GHSA-aaaa-bbbb-cccc", [], "pillow"),
            ("PYSEC-2026-1", [], "pillow"),
            ("CVE-2026-4444", ["GHSA-aaaa-bbbb-cccc", "PYSEC-2026-1"], "pillow"),
        ],
        runtime=["pillow"],
    )
    assert gate == 1


def test_a_fix_both_scanners_report_is_listed_once(tmp_path):
    """The image fragment lists it with Trivy's severity; the audit table points there."""
    trivy = tmp_path / "fragment.json"
    _run(
        "diff",
        "--label",
        "image",
        "--before",
        str(_write_report(tmp_path / "before.json", PILLOW_TRIVY)),
        "--after",
        str(_write_report(tmp_path / "after.json")),
        "--out",
        str(trivy),
    )
    audit = _audit_fragment(tmp_path, [PILLOW_GHSA], [], runtime=["pillow"])
    report = tmp_path / "report.md"
    _run("render", str(trivy), str(audit), "--out", str(report))
    text = report.read_text()
    assert "| MEDIUM | `Pillow` |" in text
    assert "GHSA-aaaa-bbbb-cccc" not in text
    assert "1 more already listed above, under another ID." in text


def test_a_package_for_another_platform_is_dev_only(tmp_path):
    """colorama is in the export, but only for Windows, which the images are not."""
    gate, _ = _render_audit(
        tmp_path,
        [("GHSA-dddd-eeee-ffff", [], "colorama")],
        runtime=["colorama==0.4.6 ; sys_platform == 'win32'"],
    )
    assert gate == 0


def test_exposure_lists_a_finding_without_a_fix(tmp_path):
    """uv audit reports `fix_versions: null` for an advisory with no fixed release."""
    audit = tmp_path / "audit.json"
    audit.write_text(
        json.dumps(
            {
                "summary": {"audited_packages": 3},
                "vulnerabilities": [
                    {
                        "id": "GHSA-aaaa-bbbb-cccc",
                        "dependency": {"name": "pillow", "version": "1.0"},
                        "fix_versions": None,
                        "link": None,
                    },
                    {
                        "id": "PYSEC-2026-55",
                        "dependency": {"name": "virtualenv", "version": "1.0"},
                        "fix_versions": ["2.0"],
                    },
                ],
            }
        )
    )
    report = tmp_path / "exposure.md"
    _run(
        "exposure",
        "--report",
        str(audit),
        "--runtime",
        str(_write_runtime(tmp_path / "runtime.txt", ["pillow"])),
        "--out",
        str(report),
    )
    text = report.read_text()
    assert "2 known vulnerabilities in 3 packages." in text
    assert "| GHSA-aaaa-bbbb-cccc | - | `pillow` | 1.0 | - |" in text
    assert "<summary>In dev-only packages (1)</summary>" in text
