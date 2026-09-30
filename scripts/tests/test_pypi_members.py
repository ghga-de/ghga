"""Tests for pypi_members.py's member JSON, which the publish workflows read."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
