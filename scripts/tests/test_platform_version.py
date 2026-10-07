"""Tests for platform_version.py's rule turning `git describe` into a version."""

import subprocess
import sys
from pathlib import Path

import pytest
from packaging.version import Version

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from platform_version import (
    FALLBACK,
    _precedence,
    cd_version,
    from_describe,
    platform_version,
)


@pytest.mark.parametrize(
    "described, expected",
    [
        ("ghga/15.3.1", "15.3.1"),
        ("ghga/15.3.1-rc.8", "15.3.1-rc.8"),
        ("ghga/15.3.1-dirty", "15.3.1+dirty"),
        ("ghga/15.3.1-rc.8-71-g44594f5", "15.3.1-rc.8+dev.71.44594f5"),
        ("ghga/15.3.1-rc.8-71-g44594f5c-dirty", "15.3.1-rc.8+dev.71.44594f5c.dirty"),
        ("v1.0.0", FALLBACK),
        ("", FALLBACK),
    ],
)
def test_from_describe(described, expected):
    """Tags, commits after them, longer SHAs and local changes map as releases.md says."""
    assert from_describe(described) == expected


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def test_checkout(tmp_path):
    """A real repo: fallback before any tag, the tag at it, build metadata after it."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.org")
    _git(tmp_path, "config", "user.name", "test")
    (tmp_path / "file").write_text("1")
    _git(tmp_path, "add", "file")
    _git(tmp_path, "commit", "-qm", "first")
    assert platform_version(tmp_path) == FALLBACK

    _git(tmp_path, "tag", "ghga/15.3.1")
    assert platform_version(tmp_path) == "15.3.1"

    (tmp_path / "file").write_text("2")
    assert platform_version(tmp_path) == "15.3.1+dirty"

    _git(tmp_path, "commit", "-qam", "second")
    version = platform_version(tmp_path)
    assert version.startswith("15.3.1+dev.1.")
    assert len(version.rsplit(".", 1)[1]) >= 7


def test_no_repo(tmp_path):
    assert platform_version(tmp_path) == FALLBACK


@pytest.mark.parametrize(
    "tags, expected",
    [
        (["ghga/15.3.1-rc.8"], "15.3.1-rc.8.dev.19401"),
        (["ghga/15.3.1-rc.9", "ghga/15.3.1-rc.10"], "15.3.1-rc.10.dev.19401"),
        (["ghga/15.3.1-rc.8", "ghga/15.3.1"], "15.3.2-dev.19401"),
        (["ghga/15.4.0-rc.1", "ghga/15.3.2"], "15.4.0-rc.1.dev.19401"),
        (["ghga/15.10.0", "ghga/15.9.0"], "15.10.1-dev.19401"),
        (["ghga/not-a-version", "other/1.0.0"], "0.0.0-dev.19401"),
        ([], "0.0.0-dev.19401"),
    ],
)
def test_cd_version(tags, expected):
    """The highest tag by semver, not by text; a final tag moves on to the next patch."""
    assert cd_version(tags, 19401) == expected


@pytest.mark.parametrize(
    "older, newer",
    [
        (["ghga/15.3.1-rc.8"], ["ghga/15.3.1-rc.8", "ghga/15.3.1"]),
        (["ghga/15.3.1-rc.8", "ghga/15.3.1"], ["ghga/15.3.1", "ghga/15.4.0-rc.1"]),
        (["ghga/15.4.0-rc.1"], ["ghga/15.4.0-rc.1", "ghga/15.3.2"]),
    ],
)
def test_cd_version_rises(older, newer):
    """A later run that sees more tags, hotfixes included, sorts higher in both schemes.

    The CD tool orders by semver, FIS's check of the DHFS version by PEP 440.
    """
    old, new = cd_version(older, 100), cd_version(newer, 200)
    assert _precedence(new) > _precedence(old)
    assert Version(new) > Version(old)
