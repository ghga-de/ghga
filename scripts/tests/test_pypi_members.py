"""Tests for pypi_members.py's member JSON and its version check per lane."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pypi_members
from pypi_members import Member


def _member(version: str) -> Member:
    return Member(
        path="libs/demo_lib",
        package="demo_lib",
        version=version,
        requires_python=">=3.11",
        internal_deps=(),
        train_deps=(),
        extras=(),
        pythons=("3.13",),
    )


@pytest.mark.parametrize(
    "version, prerelease",
    [
        ("2.0.0", False),
        ("2.0.0.post1", False),
        ("2.0.0rc1", True),
        ("2.0.0-rc.1", True),
        ("2.0.0.dev0", True),
        ("", False),
    ],
)
def test_json_says_whether_the_version_is_a_prerelease(version, prerelease):
    data = _member(version).as_json()
    assert data["prerelease"] is prerelease
    assert data["tag"] == f"demo-lib/{version}"


def _write_member(
    root: Path, path: str, version: str, deps: tuple[str, ...] = (), markers: str = ""
) -> None:
    manifest = root / path / "pyproject.toml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        f'[project]\nname = "{Path(path).name}"\nversion = "{version}"\n'
        f"dependencies = {json.dumps(list(deps))}\n{markers}"
    )


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A repo root with one member per lane, all declaring what their lane requires."""
    monkeypatch.setattr(pypi_members, "ROOT", tmp_path)
    _write_member(tmp_path, "services/auth-service", "0.0.0", ("hexkit>=10",))
    _write_member(
        tmp_path,
        "libs/metldata",
        "0.0.0",
        markers='[tool.ghga]\nrelease = "platform"\n',
    )
    _write_member(tmp_path, "libs/hexkit", "10.0.0")
    _write_member(tmp_path, "tools/demo-tool", "1.0.0")
    portal = tmp_path / "frontend/data-portal/package.json"
    portal.parent.mkdir(parents=True)
    portal.write_text('{"name": "data-portal", "version": "0.0.0"}')
    return tmp_path


def test_versions_per_lane_pass(repo):
    """PyPI and no-lane members keep their versions; platform members declare 0.0.0."""
    assert pypi_members.version_errors() == []
    assert pypi_members.main(["--check-versions"]) == 0


def test_platform_member_with_a_version_fails(repo, capsys):
    (repo / "services/auth-service/pyproject.toml").write_text(
        '[project]\nname = "auth-service"\nversion = "10.0.2"\n'
    )

    assert pypi_members.main(["--check-versions"]) == 1
    error = capsys.readouterr().err
    assert "services/auth-service" in error
    assert "ADR-0046" in error


def test_front_end_with_a_version_fails(repo):
    (repo / "frontend/data-portal/package.json").write_text('{"version": "2.5.16"}')

    [error] = pypi_members.version_errors()
    assert "frontend/data-portal/package.json" in error


@pytest.mark.parametrize("spec", ["metldata>=4", "Metldata", "auth_service"])
def test_pypi_member_depending_on_platform_member_fails(tmp_path, monkeypatch, spec):
    """Its wheel would require a version that is never published."""
    monkeypatch.setattr(pypi_members, "ROOT", tmp_path)
    _write_member(tmp_path, "services/auth-service", "0.0.0")
    _write_member(
        tmp_path,
        "libs/metldata",
        "0.0.0",
        markers='[tool.ghga]\nrelease = "platform"\n',
    )
    _write_member(tmp_path, "libs/hexkit", "10.0.0", (spec,))

    [error] = pypi_members.version_errors()
    assert error.startswith("hexkit is on the PyPI lane")
