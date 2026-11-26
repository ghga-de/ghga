"""Tests for image_members.py's command line, which the image recipes read."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import image_members

MEMBERS = [
    {"path": "services/a", "package": "a", "kind": "python"},
    {"path": "services/b", "package": "b", "kind": "python"},
    {"path": "frontend/portal", "package": "portal", "kind": "frontend"},
]


@pytest.fixture(autouse=True)
def fixed_members(monkeypatch):
    """Two Python members and one front end, instead of the repo's own."""
    monkeypatch.setattr(image_members, "image_members", lambda: MEMBERS)


def _main(capsys, *argv: str) -> str:
    image_members.main(list(argv))
    return capsys.readouterr().out


def test_no_options_print_every_member_as_json(capsys):
    """The JSON output is what release.yaml and the chart generator read."""
    assert json.loads(_main(capsys)) == MEMBERS


def test_field_prints_one_member_per_line(capsys):
    """`--field` gives the shell recipes a plain list to loop over."""
    out = _main(capsys, "--field", "path")
    assert out.splitlines() == ["services/a", "services/b", "frontend/portal"]


def test_kind_keeps_only_that_kind(capsys):
    """`just demo-load mono` loads the front-end images next to the platform image."""
    out = _main(capsys, "--kind", "frontend", "--field", "package")
    assert out.splitlines() == ["portal"]


def test_kind_filters_the_json_too(capsys):
    """`--kind` applies with or without `--field`."""
    assert json.loads(_main(capsys, "--kind", "python")) == MEMBERS[:2]
