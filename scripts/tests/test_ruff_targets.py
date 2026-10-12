"""Tests that ruff's target versions match the Python floors of the code they cover.

ruff reads requires-python only from the pyproject.toml holding its config, and the
root one has no [project], so the root [tool.ruff] states the targets itself. These
tests fail when a member's floor moves without its target, or the other way round.
"""

import re
import tomllib
from pathlib import Path, PurePosixPath

import pytest

ROOT = Path(__file__).resolve().parents[2]

# not workspace members: they run on the workspace interpreter (.python-version)
WORKSPACE_INTERPRETER_DIRS = ("scripts", "deploy")


def _ruff_config() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["ruff"]


def _members() -> list[str]:
    return sorted(
        manifest.parent.relative_to(ROOT).as_posix()
        for root in ("libs", "services", "tools")
        for manifest in (ROOT / root).glob("*/pyproject.toml")
    )


def _as_target(version: str) -> str:
    """Turn `3.13` into ruff's spelling, `py313`."""
    return "py" + version.replace(".", "")


def _floor(member: str) -> str:
    project = tomllib.loads((ROOT / member / "pyproject.toml").read_text())["project"]
    match = re.fullmatch(r">=\s*(3\.\d+)", project["requires-python"].strip())
    assert match, f"{member}: requires-python is not a plain >= floor"
    return match.group(1)


def _target_for(directory: str) -> str:
    """The target ruff applies to the files in `directory`."""
    config = _ruff_config()
    probe = PurePosixPath(directory, "module.py")
    matching = [
        target
        for pattern, target in config.get("per-file-target-version", {}).items()
        if probe.full_match(pattern)
    ]
    assert len(matching) <= 1, f"{directory}: several per-file targets match"
    return matching[0] if matching else config["target-version"]


@pytest.mark.parametrize("member", _members())
def test_member_target_is_its_floor(member: str):
    """Each member is checked against the Python version its requires-python allows."""
    assert _target_for(member) == _as_target(_floor(member))


@pytest.mark.parametrize("directory", WORKSPACE_INTERPRETER_DIRS)
def test_non_member_target_is_the_workspace_interpreter(directory: str):
    """Code outside the members is checked against the workspace interpreter."""
    version = (ROOT / ".python-version").read_text().strip()
    assert _target_for(directory) == _as_target(version)


def test_global_target_is_the_lowest_floor():
    """Members at the lowest floor need no per-file target of their own."""
    lowest = min(
        (_floor(member) for member in _members()),
        key=lambda version: tuple(int(part) for part in version.split(".")),
    )
    assert _ruff_config()["target-version"] == _as_target(lowest)


def test_every_per_file_target_covers_code():
    """A pattern left behind by a removed or renamed member is caught."""
    directories = [*_members(), *WORKSPACE_INTERPRETER_DIRS]
    for pattern in _ruff_config().get("per-file-target-version", {}):
        assert any(
            PurePosixPath(directory, "module.py").full_match(pattern)
            for directory in directories
        ), f"{pattern} matches no member and no workspace-interpreter directory"
