"""Unit tests for the image reference the chart generator derives per member."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from create_charts import MONO_IMAGE, derived_values, image_name

PYTHON_MEMBER = {"package": "wps", "kind": "python"}
FRONTEND_MEMBER = {"package": "data-portal", "kind": "frontend"}


@pytest.mark.parametrize(
    "member, mono, expected",
    [
        (PYTHON_MEMBER, False, "wps"),
        (PYTHON_MEMBER, True, MONO_IMAGE),
        (FRONTEND_MEMBER, False, "data-portal"),
        (FRONTEND_MEMBER, True, "data-portal"),
    ],
)
def test_image_name(member, mono, expected):
    """Only Python members move to the mono image; the front end keeps its own."""
    assert image_name(member, mono) == expected


def test_mono_keeps_the_member_executable():
    """The mono image starts each service by its own console script."""
    values = derived_values(PYTHON_MEMBER, "ghcr.io/ghga-de/ghga", mono=True)
    assert values["image"] == {
        "registry": "ghcr.io",
        "repository": f"ghga-de/ghga/{MONO_IMAGE}",
    }
    assert values["executable"] == "wps"
