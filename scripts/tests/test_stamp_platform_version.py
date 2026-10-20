"""Tests for stamp_platform_version.py's rewrite of installed dist-infos.

Each test builds fake dist-infos in a temporary site-packages and points the script's
`distributions()` at them, so no real environment is touched.
"""

import json
import sys
from importlib.metadata import Distribution
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import stamp_platform_version as stamp

PLATFORM = "15.3.1"


def _install(site: Path, name: str, version: str, *, workspace: bool = True) -> Path:
    """Writes a minimal dist-info, from workspace source unless `workspace` is false."""
    dist_info = site / f"{name.replace('-', '_')}-{version}.dist-info"
    dist_info.mkdir(parents=True)
    (dist_info / "METADATA").write_text(
        f"Metadata-Version: 2.4\nName: {name}\nVersion: {version}\n"
    )
    (dist_info / "RECORD").write_text(f"{dist_info.name}/METADATA,sha256=x,1\n")
    url = "file:///app/libs/x" if workspace else "https://files.example/x.whl"
    (dist_info / "direct_url.json").write_text(json.dumps({"url": url}))
    return dist_info


def _version(dist_info: Path) -> str:
    return Distribution.at(dist_info).version


@pytest.fixture
def site(tmp_path, monkeypatch):
    """An empty site-packages that the script's `distributions()` lists."""
    monkeypatch.setattr(
        stamp,
        "distributions",
        lambda: [Distribution.at(p) for p in sorted(tmp_path.iterdir())],
    )
    return tmp_path


def test_log_names_each_version_once(site, capsys):
    _install(site, "hexkit", "10.0.0")

    stamp.main(["--version", PLATFORM])

    assert f"suffixed  hexkit: 10.0.0+ghga.{PLATFORM}\n" in capsys.readouterr().out


def test_stamps_every_placeholder_member(site):
    """Platform-lane members get the version; PyPI-lane and registry installs do not."""
    service = _install(site, "auth-service", "0.0.0")
    metldata = _install(site, "metldata", "0.0.0")
    hexkit = _install(site, "hexkit", "10.0.0")
    pydantic = _install(site, "pydantic", "2.12.0", workspace=False)

    assert stamp.main(["--version", PLATFORM, "--package", "auth-service"]) == 0

    assert _version(service) == PLATFORM
    assert _version(metldata) == PLATFORM
    assert _version(hexkit) == f"10.0.0+ghga.{PLATFORM}"
    assert _version(pydantic) == "2.12.0"


def test_record_matches_rewritten_metadata(site):
    """The RECORD hash of METADATA follows the rewrite, so the dist-info stays valid."""
    service = _install(site, "auth-service", "0.0.0")

    stamp.main(["--version", PLATFORM])

    expected = stamp._record_entry(service, service / "METADATA")
    assert (service / "RECORD").read_text() == expected + "\n"


def test_without_package_stamps_all(site):
    """The mono image names no member and still gets every one stamped."""
    members = [_install(site, n, "0.0.0") for n in ("auth-service", "ucs", "wps")]

    assert stamp.main(["--version", "0.0.0-dev.1201"]) == 0

    assert {_version(m) for m in members} == {"0.0.0-dev.1201"}


def test_build_metadata_in_suffix(site):
    """A `+` in the platform version becomes a dot in the PEP 440 local suffix."""
    hexkit = _install(site, "hexkit", "10.0.0")

    stamp.main(["--version", "0.0.0+dev"])

    assert _version(hexkit) == "10.0.0+ghga.0.0.0.dev"


def test_package_without_placeholder_fails(site, capsys):
    """A released member that declares a real version was not stamped, which fails."""
    _install(site, "auth-service", "10.0.2")

    assert stamp.main(["--version", PLATFORM, "--package", "auth_service"]) == 1
    assert "auth_service" in capsys.readouterr().err


def test_missing_package_fails(site):
    _install(site, "ucs", "0.0.0")

    assert stamp.main(["--version", PLATFORM, "--package", "auth-service"]) == 1


def test_rerun_changes_nothing(site):
    """A second run neither fails the package check nor suffixes stamped members."""
    service = _install(site, "auth-service", "0.0.0")
    hexkit = _install(site, "hexkit", "10.0.0")
    args = ["--version", PLATFORM, "--package", "auth-service"]

    assert stamp.main(args) == 0
    assert stamp.main(args) == 0

    assert _version(service) == PLATFORM
    assert _version(hexkit) == f"10.0.0+ghga.{PLATFORM}"
