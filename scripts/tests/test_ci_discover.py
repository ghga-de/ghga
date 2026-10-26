"""Tests for ci_discover.py, the outputs of ci.yaml's `discover` job."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ci_discover

MEMBERS = [
    {
        "path": "services/a",
        "package": "a",
        "kind": "python",
        "dockerfile": "docker/Dockerfile",
    },
    {
        "path": "services/b",
        "package": "b",
        "kind": "python",
        "dockerfile": "docker/Dockerfile",
    },
    {
        "path": "frontend/portal",
        "package": "portal",
        "kind": "frontend",
        "dockerfile": "frontend/portal/Dockerfile",
    },
]


def test_split_keeps_only_the_named_roots():
    """Targets are split by their top-level directory."""
    targets = ["deploy/charts/x", "frontend/portal", "libs/l", "services/s", "testbed"]
    assert ci_discover.split(targets, "libs", "services") == ["libs/l", "services/s"]
    assert ci_discover.split(targets, "frontend") == ["frontend/portal"]


def test_unchanged_dockerfiles_build_nothing():
    """A change set that touches no Dockerfile builds no image."""
    assert ci_discover.image_builds(["uv.lock"], MEMBERS) == {}


def test_shared_dockerfile_builds_the_mono_image_once():
    """The Python members share docker/Dockerfile, so one mono build covers them all."""
    builds = ci_discover.image_builds(["docker/Dockerfile"], MEMBERS)
    assert builds == {"platform": "image-mono"}


def test_own_dockerfile_builds_that_member():
    """A member with its own Dockerfile builds through `just image <path>`."""
    builds = ci_discover.image_builds(["frontend/portal/Dockerfile"], MEMBERS)
    assert builds == {"portal": "image frontend/portal"}


def test_unknown_change_set_builds_every_image():
    """No change set to compare against means every image counts as changed."""
    builds = ci_discover.image_builds(None, MEMBERS)
    assert list(builds) == ["platform", "portal"]


def test_unresolvable_base_checks_everything():
    """A base that does not resolve must mean "check everything", not "check nothing"."""
    outputs = ci_discover.discover("origin/no-such-ref-for-tests")
    assert json.loads(outputs["devcontainer"]) is True
    assert json.loads(outputs["python"])
    assert "platform" in json.loads(outputs["images"])
