"""Tests for the CLI.

Copyright by The GHGA Authors.
SPDX-License-Identifier: Apache-2.0
"""

import json

import pytest

from jsonsubschema.cli import main


@pytest.fixture()
def schema_files(tmp_path):
    lhs = tmp_path / "lhs.json"
    rhs = tmp_path / "rhs.json"

    def write(lhs_schema, rhs_schema):
        lhs.write_text(json.dumps(lhs_schema))
        rhs.write_text(json.dumps(rhs_schema))
        return str(lhs), str(rhs)

    return write


def test_cli_subschema_true(schema_files, monkeypatch, capsys):
    lhs_path, rhs_path = schema_files({"type": "integer"}, {"type": "number"})
    monkeypatch.setattr("sys.argv", ["jsonsubschema", lhs_path, rhs_path])
    main()
    assert capsys.readouterr().out.strip() == "LHS <: RHS True"


def test_cli_subschema_false(schema_files, monkeypatch, capsys):
    lhs_path, rhs_path = schema_files({"type": "number"}, {"type": "integer"})
    monkeypatch.setattr("sys.argv", ["jsonsubschema", lhs_path, rhs_path])
    main()
    assert capsys.readouterr().out.strip() == "LHS <: RHS None"


def test_cli_readme_example(schema_files, monkeypatch, capsys):
    """s2 (non-empty strings/nulls) is a subschema of s1 (all strings/nulls)."""
    lhs_path, rhs_path = schema_files(
        {"type": ["string", "null"], "not": {"enum": [""]}},
        {"type": ["null", "string"]},
    )
    monkeypatch.setattr("sys.argv", ["jsonsubschema", lhs_path, rhs_path])
    main()
    assert capsys.readouterr().out.strip() == "LHS <: RHS True"
