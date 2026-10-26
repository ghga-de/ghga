"""Tests for pypi_members.py's member JSON, its version check per lane and the
blocked-cell table that keeps a member off a Python version its dependencies
cannot install on."""

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
        blocked_pythons=(),
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


@pytest.mark.parametrize(
    "filename, supported",
    [
        # A version-specific wheel fits that version alone.
        ("crypt4gh-1.8.6-cp315-cp315-manylinux_2_17_x86_64.whl", True),
        ("crypt4gh-1.8.6-cp315-cp315-linux_x86_64.whl", True),
        ("crypt4gh-1.8.6-cp314-cp314-manylinux_2_17_x86_64.whl", False),
        # Pure Python fits everything.
        ("crypt4gh-1.8.6-py3-none-any.whl", True),
        # The stable ABI fits its own version and every later one, so a project moving
        # to abi3 counts as having shipped for 3.15.
        ("crypt4gh-1.8.6-cp311-abi3-manylinux_2_28_x86_64.whl", True),
        ("crypt4gh-1.8.6-cp316-abi3-manylinux_2_28_x86_64.whl", False),
        # Shipped for 3.15, but not for the runner the matrix uses, so the cell it
        # guards still cannot install and the entry has to stay.
        ("crypt4gh-1.8.6-cp315-cp315-macosx_11_0_arm64.whl", False),
        ("crypt4gh-1.8.6-cp315-cp315-win_amd64.whl", False),
        ("crypt4gh-1.8.6-cp315-cp315-manylinux_2_17_aarch64.whl", False),
        ("crypt4gh-1.8.6-cp315-cp315-musllinux_1_2_x86_64.whl", False),
        # Free-threaded build; the matrix runs the stock interpreter.
        ("crypt4gh-1.8.6-cp315-cp315t-manylinux_2_17_x86_64.whl", False),
        ("not-a-wheel.txt", False),
    ],
)
def test_wheel_support_reads_the_interpreter_tag(filename, supported):
    assert pypi_members._wheel_supports(filename, "3.15") is supported


def test_blocked_versions_leave_the_members_matrix(monkeypatch):
    """The member still declares the version; only its cell is dropped."""
    monkeypatch.setattr(
        pypi_members, "BLOCKED_CELLS", {("libs/hexkit", "3.15"): "crypt4gh"}
    )

    assert pypi_members._supported_pythons(">=3.13", "libs/hexkit") == ("3.13", "3.14")
    assert pypi_members._supported_pythons(">=3.13", "libs/schemapack") == (
        "3.13",
        "3.14",
        "3.15",
    )


def _stub_index(monkeypatch, **projects) -> None:
    """Answers for `_pypi_project`, so no test reaches the network."""
    defaults = {"reachable": True, "versions": {"1.0"}, "latest": "1.0"}
    monkeypatch.setattr(
        pypi_members,
        "_pypi_project",
        lambda package: {**defaults, **projects.get(package, {"latest_wheels": ()})},
    )


def test_a_blocker_without_the_wheel_keeps_its_entry(repo, monkeypatch, capsys):
    monkeypatch.setattr(
        pypi_members, "BLOCKED_CELLS", {("libs/hexkit", "3.15"): "crypt4gh"}
    )
    _stub_index(
        monkeypatch,
        crypt4gh={
            "latest_wheels": ("crypt4gh-1.0-cp314-cp314-manylinux_2_17_x86_64.whl",)
        },
    )

    assert pypi_members.blocked_cell_errors() == []
    assert pypi_members.main(["--check-blocked-cells"]) == 0
    assert "libs/hexkit is not tested on Python 3.15" in capsys.readouterr().out


def test_a_blocker_that_shipped_the_wheel_fails_and_names_the_edits(
    repo, monkeypatch, capsys
):
    """The entry costs coverage, so going stale is a failure, not a warning."""
    monkeypatch.setattr(
        pypi_members, "BLOCKED_CELLS", {("libs/hexkit", "3.15"): "crypt4gh"}
    )
    _stub_index(
        monkeypatch,
        crypt4gh={
            "latest": "1.8.7",
            "latest_wheels": ("crypt4gh-1.8.7-cp315-cp315-manylinux_2_17_x86_64.whl",),
        },
    )

    assert pypi_members.main(["--check-blocked-cells"]) == 1
    error = capsys.readouterr().err
    assert "crypt4gh 1.8.7 now ships a wheel for Python 3.15" in error
    for edit in ("scripts/pypi_members.py", "pyproject.toml", "docs/dependencies.md"):
        assert edit in error


def test_an_unreachable_index_leaves_the_entry_alone(repo, monkeypatch):
    """Same as release_candidates: a failed query is not evidence about the wheel."""
    monkeypatch.setattr(
        pypi_members, "BLOCKED_CELLS", {("libs/hexkit", "3.15"): "crypt4gh"}
    )
    _stub_index(monkeypatch, crypt4gh={"reachable": False, "latest_wheels": ()})

    assert pypi_members.blocked_cell_errors() == []


def test_a_blocker_the_index_never_published_fails(repo, monkeypatch):
    """A renamed or yanked blocker can never ship the wheel that retires the entry."""
    monkeypatch.setattr(
        pypi_members, "BLOCKED_CELLS", {("libs/hexkit", "3.15"): "crypt4gh"}
    )
    _stub_index(
        monkeypatch, crypt4gh={"versions": set(), "latest": None, "latest_wheels": ()}
    )

    [error] = pypi_members.blocked_cell_errors()
    assert "PyPI has never published" in error


def test_a_blocked_path_outside_the_lane_fails(repo, monkeypatch):
    monkeypatch.setattr(
        pypi_members, "BLOCKED_CELLS", {("libs/renamed-lib", "3.15"): "crypt4gh"}
    )
    _stub_index(monkeypatch)

    [error] = pypi_members.blocked_cell_errors()
    assert "not a PyPI-lane member" in error


def test_the_repos_own_blocked_cells_name_real_members_and_versions():
    """Offline structural check on the committed table, with no index lookup."""
    lane_paths = {member.path for member in pypi_members.pypi_members()}
    for (path, python), blocker in pypi_members.BLOCKED_CELLS.items():
        assert path in lane_paths, path
        assert python in pypi_members.TEST_PYTHONS, python
        assert blocker


def _cell_member(**fields) -> Member:
    return Member(
        **{
            "path": "libs/demo_lib",
            "package": "demo_lib",
            "version": "1.0.0",
            "requires_python": ">=3.13",
            "internal_deps": ("libs/a", "libs/b"),
            "train_deps": ("libs/a", "libs/b"),
            "extras": ("s3", "mongo"),
            "pythons": ("3.13", "3.14"),
            "blocked_pythons": (),
            **fields,
        }
    )


def test_cell_fields_are_one_per_line():
    """Package, extras and train deps each take one line, empty ones included."""
    assert pypi_members.cell_fields(_cell_member(), "3.13") == (
        "demo_lib\ns3,mongo\nlibs/a libs/b"
    )
    bare = _cell_member(extras=(), train_deps=())
    assert pypi_members.cell_fields(bare, "3.14").split("\n") == ["demo_lib", "", ""]


def test_cell_on_a_blocked_python_names_the_blocker():
    """A dropped cell says which dependency ships no wheel."""
    member = _cell_member(blocked_pythons=(("3.15", "crypt4gh"),))
    with pytest.raises(ValueError, match="crypt4gh ships no wheel"):
        pypi_members.cell_fields(member, "3.15")


def test_cell_outside_the_declared_range_lists_where_it_runs():
    """A version the member does not declare names the ones it does run on."""
    with pytest.raises(ValueError, match=r"so it runs on: 3\.13, 3\.14"):
        pypi_members.cell_fields(_cell_member(), "3.11")


@pytest.mark.parametrize(
    "argv",
    [
        ["--cell", "3.13"],
        ["--cell", "3.13", "--paths", "libs/a", "libs/b"],
        ["--cell", "3.13", "--paths", "libs/a", "--members"],
    ],
)
def test_cell_needs_exactly_one_member(argv):
    with pytest.raises(SystemExit):
        pypi_members.main(argv)


def test_cell_for_a_non_lane_member_points_at_the_marker():
    with pytest.raises(SystemExit, match="not a PyPI-lane member"):
        pypi_members.main(["--cell", "3.13", "--paths", "services/auth-service"])
