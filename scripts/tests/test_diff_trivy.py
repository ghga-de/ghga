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


# The Result.Type of each Class, unless a finding names another.
TYPES = {"os-pkgs": "alpine", "lang-pkgs": "python-pkg"}


def _write_report(path, *findings):
    """Write a Trivy JSON report of (class, id, package[, fields]) findings.

    `fields` adds to or overrides the vulnerability's fields; its "Type" is the
    section's.
    """
    results: dict[tuple[str, str], list[dict]] = {}
    for result_class, vuln_id, package, *rest in findings:
        fields = dict(rest[0]) if rest else {}
        result_type = fields.pop("Type", TYPES[result_class])
        results.setdefault((result_class, result_type), []).append(
            {
                "VulnerabilityID": vuln_id,
                "PkgName": package,
                "InstalledVersion": "1.0",
                "FixedVersion": "2.0",
                "Severity": "MEDIUM",
                "PrimaryURL": f"https://example.org/{vuln_id}",
                **fields,
            }
        )
    report = {
        "Results": [
            {
                "Target": result_type,
                "Class": result_class,
                "Type": result_type,
                "Vulnerabilities": vulns,
            }
            for (result_class, result_type), vulns in results.items()
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


def _trivy_fragment(tmp_path, before, after, name="fragment"):
    """Diff two Trivy reports into the fragment `name`.json."""
    fragment = tmp_path / f"{name}.json"
    _run(
        "diff",
        "--label",
        name,
        "--before",
        str(_write_report(tmp_path / f"{name}-before.json", *before)),
        "--after",
        str(_write_report(tmp_path / f"{name}-after.json", *after)),
        "--out",
        str(fragment),
    )
    return fragment


def _scan(tmp_path, before, after):
    """Diff then render as the workflow does; return its gate count and report."""
    fragment = _trivy_fragment(tmp_path, before, after)
    report = tmp_path / "report.md"
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


# uv audit findings as (id, aliases, package[, version]); the CVE alias of PILLOW_GHSA is the
# ID Trivy reports for the same advisory.
PILLOW_GHSA = ("GHSA-aaaa-bbbb-cccc", ["CVE-2026-4444"], "pillow")
PILLOW_TRIVY = ("lang-pkgs", "CVE-2026-4444", "Pillow")
VIRTUALENV: tuple[str, list[str], str] = ("PYSEC-2026-55", [], "virtualenv")


SCHEMA = {"version": "preview"}


def _write_audit(path, *findings):
    """Write a uv audit JSON report of (id, aliases, package[, version]) findings."""
    vulns = [
        {
            "id": vuln_id,
            "aliases": aliases,
            "dependency": {
                "name": package,
                "version": version[0] if version else "1.0",
            },
            "fix_versions": ["2.0"],
            "link": f"https://example.org/{vuln_id}",
        }
        for vuln_id, aliases, package, *version in findings
    ]
    path.write_text(json.dumps({"schema": SCHEMA, "vulnerabilities": vulns}))
    return path


def _write_runtime(path, runtime):
    """Write a `uv export` of the given names at 1.0, or of whole lines with a `=`."""
    path.write_text(
        "".join(f"{name}\n" if "=" in name else f"{name}==1.0\n" for name in runtime)
    )
    return path


def _audit_fragment(tmp_path, before, after, runtime, after_runtime=None, python=None):
    """Diff two uv audit reports, with `runtime` as the images' package names.

    `after_runtime` is what the images install after the update, `runtime` if not
    given; `python` is the images' Python version.
    """
    before_path = _write_runtime(tmp_path / "runtime-before.txt", runtime)
    after_path = _write_runtime(
        tmp_path / "runtime-after.txt",
        runtime if after_runtime is None else after_runtime,
    )
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
        "--before-runtime",
        str(before_path),
        "--after-runtime",
        str(after_path),
        *(["--python", python] if python else []),
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
    trivy = _trivy_fragment(tmp_path, [PILLOW_TRIVY, URLLIB3], [], name="image")
    gate = _run("render", str(trivy), str(audit), "--out", str(tmp_path / "report.md"))
    assert int(gate) == 2


def _render_audit(tmp_path, before, runtime, after=(), **kwargs):
    """Diff two uv audit reports, a clean one by default, and render; return gate and report.

    `kwargs` go to `_audit_fragment`.
    """
    fragment = _audit_fragment(tmp_path, before, after, runtime=runtime, **kwargs)
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
    trivy = _trivy_fragment(tmp_path, [PILLOW_TRIVY], [], name="image")
    audit = _audit_fragment(tmp_path, [PILLOW_GHSA], [], runtime=["pillow"])
    report = tmp_path / "report.md"
    _run("render", str(trivy), str(audit), "--out", str(report))
    text = report.read_text()
    assert "| MEDIUM | `Pillow` |" in text
    assert "GHSA-aaaa-bbbb-cccc" not in text
    assert "1 more already listed above." in text


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
                "schema": SCHEMA,
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


def test_one_vendor_advisory_keeps_its_cves_apart(tmp_path):
    """One distribution advisory fixes both CVEs; they are still two findings."""
    dsa = {"VendorIDs": ["DSA-6001-1"]}
    _, report = _scan(tmp_path, [(*SQLITE, dsa), (*SQLITE_2, dsa)], [])
    assert "**Fixed by the refreshed base image, not by this update (2):**" in report
    assert "CVE-2026-11824" in report


def test_a_regression_both_images_share_is_listed_in_each(tmp_path):
    """Both images carry the base package, so each carries its regression."""
    first = _trivy_fragment(tmp_path, [], [SQLITE], name="frontend")
    second = _trivy_fragment(tmp_path, [], [SQLITE], name="platform")
    report = tmp_path / "report.md"
    _run("render", str(first), str(second), "--out", str(report))
    assert report.read_text().count("**Introduced (1):**") == 2


def test_an_npm_and_a_pypi_fix_under_one_id_count_twice(tmp_path):
    """One GHSA can cover both ecosystems, and PEP 503 does not apply to npm."""
    npm = ("lang-pkgs", "GHSA-gggg-hhhh-iiii", "lodash.merge", {"Type": "pnpm"})
    frontend = _trivy_fragment(tmp_path, [npm], [], name="frontend")
    audit = _audit_fragment(
        tmp_path, [("GHSA-gggg-hhhh-iiii", [], "lodash-merge")], [], ["lodash-merge"]
    )
    gate = _run(
        "render", str(frontend), str(audit), "--out", str(tmp_path / "report.md")
    )
    assert int(gate) == 2


def test_a_fix_in_the_installed_one_of_two_versions_counts(tmp_path):
    """uv.lock holds pillow twice; the update fixes the version the images install."""
    gate, _ = _render_audit(
        tmp_path,
        [(*PILLOW_GHSA, "1.0"), (*PILLOW_GHSA, "0.9")],
        runtime=["pillow"],
        after=[(*PILLOW_GHSA, "0.9")],
    )
    assert gate == 1


def test_a_bump_that_stays_vulnerable_is_no_fix(tmp_path):
    gate, _ = _render_audit(
        tmp_path,
        [(*PILLOW_GHSA, "1.0")],
        runtime=["pillow==1.0", "pillow==1.1"],
        after=[(*PILLOW_GHSA, "1.1")],
    )
    assert gate == 0


def test_exposure_lists_adverse_statuses(tmp_path):
    audit = tmp_path / "audit.json"
    audit.write_text(
        json.dumps(
            {
                "schema": SCHEMA,
                "vulnerabilities": [],
                "adverse_statuses": [
                    {
                        "dependency": {"name": "pyyaml", "version": "6.0"},
                        "status": "archived",
                    }
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
        str(_write_runtime(tmp_path / "runtime.txt", ["pyyaml"])),
        "--out",
        str(report),
    )
    assert '- `pyyaml` 6.0: {"status": "archived"}' in report.read_text()


def test_a_dev_only_version_does_not_take_a_runtime_pair(tmp_path):
    """pillow 1.1 is still vulnerable; the dev-only 0.9 must not pair with it."""
    gate, _ = _render_audit(
        tmp_path,
        [(*PILLOW_GHSA, "0.9"), (*PILLOW_GHSA, "1.0")],
        runtime=["pillow==1.0", "pillow==1.1"],
        after=[(*PILLOW_GHSA, "1.1")],
    )
    assert gate == 0


def test_markers_hold_on_either_image_machine(tmp_path):
    """The images are built for amd64 and arm64, so both packages ship."""
    gate, _ = _render_audit(
        tmp_path,
        [("GHSA-1111-2222-3333", [], "amd"), ("GHSA-4444-5555-6666", [], "arm")],
        runtime=[
            "amd==1.0 ; platform_machine == 'x86_64'",
            "arm==1.0 ; platform_machine == 'aarch64'",
        ],
    )
    assert gate == 2


def _diff_audit_report(tmp_path, report):
    """Run the uv-audit diff with `report` as the before report; return the process."""
    before = tmp_path / "unknown.json"
    before.write_text(json.dumps(report))
    return subprocess.run(
        [
            sys.executable,
            str(DIFF_TRIVY),
            "diff",
            "--format",
            "uv-audit",
            "--label",
            "uv.lock",
            "--before",
            str(before),
            "--after",
            str(_write_audit(tmp_path / "after.json")),
            "--before-runtime",
            str(_write_runtime(tmp_path / "runtime.txt", [])),
            "--after-runtime",
            str(tmp_path / "runtime.txt"),
            "--out",
            str(tmp_path / "fragment.json"),
        ],
        capture_output=True,
        text=True,
    )


def test_a_report_of_another_schema_fails(tmp_path):
    """A format change must not read as "no findings", which could close a PR."""
    result = _diff_audit_report(
        tmp_path, {"schema": {"version": "1"}, "vulnerabilities": []}
    )
    assert result.returncode != 0
    assert "schema '1'" in result.stderr


def test_a_report_without_vulnerabilities_fails(tmp_path):
    result = _diff_audit_report(tmp_path, {"schema": SCHEMA, "findings": []})
    assert result.returncode != 0


def test_fixes_in_two_installed_versions_count_as_listed(tmp_path):
    """The images install pillow twice, by marker; the gate counts the rows listed."""
    gate, report = _render_audit(
        tmp_path,
        [(*PILLOW_GHSA, "1.0"), (*PILLOW_GHSA, "0.9")],
        runtime=["pillow==1.0", "pillow==0.9"],
    )
    assert gate == 2
    assert "**Fixed by the dependency update (2):**" in report


def test_a_package_moved_into_the_images_is_introduced(tmp_path):
    """pillow 1.0 was dev-only; the update installs it in the images, still vulnerable."""
    gate, report = _render_audit(
        tmp_path,
        [PILLOW_GHSA],
        runtime=[],
        after=[PILLOW_GHSA],
        after_runtime=["pillow"],
    )
    assert gate == 0
    assert "**Introduced (1):**" in report


def test_dev_only_regressions_are_folded_away(tmp_path):
    gate, report = _render_audit(tmp_path, [], runtime=["pillow"], after=[VIRTUALENV])
    assert gate == 0
    assert "<summary>Introduced in dev-only packages (1)</summary>" in report
    assert "**Introduced" not in report


def test_markers_hold_for_the_images_python(tmp_path):
    """The marker holds for the images' Python only, not for the one running the script."""
    gate, _ = _render_audit(
        tmp_path,
        [("GHSA-1111-2222-3333", [], "older")],
        runtime=["older==1.0 ; python_full_version == '3.13.1'"],
        python="3.13.1",
    )
    assert gate == 1


def test_only_adverse_statuses_the_update_introduced_are_listed(tmp_path):
    def audit(name, *packages):
        path = tmp_path / name
        statuses = [
            {"dependency": {"name": p, "version": "1.0"}, "status": "yanked"}
            for p in packages
        ]
        path.write_text(
            json.dumps(
                {"schema": SCHEMA, "vulnerabilities": [], "adverse_statuses": statuses}
            )
        )
        return path

    runtime = _write_runtime(tmp_path / "runtime.txt", [])
    fragment = tmp_path / "fragment.json"
    _run(
        "diff",
        "--format",
        "uv-audit",
        "--label",
        "uv.lock",
        "--before",
        str(audit("before.json", "pyyaml")),
        "--after",
        str(audit("after.json", "pyyaml", "attrs")),
        "--before-runtime",
        str(runtime),
        "--after-runtime",
        str(runtime),
        "--out",
        str(fragment),
    )
    assert json.loads(fragment.read_text())["adverse"] == [
        '`attrs` 1.0: {"status": "yanked"}'
    ]


def test_an_advisory_trivy_lists_under_two_ids_counts_once(tmp_path):
    """Only uv audit's alias joins Trivy's CVE and GHSA rows of one pillow version."""
    trivy = _trivy_fragment(
        tmp_path,
        [PILLOW_TRIVY, ("lang-pkgs", "GHSA-aaaa-bbbb-cccc", "pillow")],
        [],
        name="image",
    )
    audit = _audit_fragment(tmp_path, [PILLOW_GHSA], [], runtime=["pillow"])
    gate = _run("render", str(trivy), str(audit), "--out", str(tmp_path / "report.md"))
    assert int(gate) == 1


def test_a_status_kept_through_a_version_bump_is_not_introduced(tmp_path):
    def audit(name, version):
        path = tmp_path / name
        status = {"dependency": {"name": "pyyaml", "version": version}, "status": "x"}
        path.write_text(
            json.dumps(
                {"schema": SCHEMA, "vulnerabilities": [], "adverse_statuses": [status]}
            )
        )
        return path

    runtime = _write_runtime(tmp_path / "runtime.txt", [])
    fragment = tmp_path / "fragment.json"
    _run(
        "diff",
        "--format",
        "uv-audit",
        "--label",
        "uv.lock",
        "--before",
        str(audit("before.json", "6.0")),
        "--after",
        str(audit("after.json", "6.1")),
        "--before-runtime",
        str(runtime),
        "--after-runtime",
        str(runtime),
        "--out",
        str(fragment),
    )
    assert json.loads(fragment.read_text())["adverse"] == []


def test_a_dev_only_regression_does_not_hide_a_shipped_one(tmp_path):
    """The audit's dev-only row comes first, but the image's row is still listed."""
    audit = _audit_fragment(tmp_path, [], [PILLOW_GHSA], runtime=[], after_runtime=[])
    trivy = _trivy_fragment(tmp_path, [], [PILLOW_TRIVY], name="image")
    report = tmp_path / "report.md"
    _run("render", str(audit), str(trivy), "--out", str(report))
    text = report.read_text()
    assert "**Introduced (1):**" in text
    assert "already listed above" not in text


def test_a_merge_into_a_still_vulnerable_version_is_no_fix(tmp_path):
    gate, _ = _render_audit(
        tmp_path,
        [(*PILLOW_GHSA, "1.0"), (*PILLOW_GHSA, "1.1")],
        runtime=["pillow==1.0", "pillow==1.1", "pillow==1.2"],
        after=[(*PILLOW_GHSA, "1.2")],
    )
    assert gate == 0
