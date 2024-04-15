# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test the cli.

Please note, these tests will just shallowly test that the cli commands can be called
and produce the expected output. However, the output is not deeply investigated and
only a single senario is tester for each command. More deeper testing is done on the
python API (to avoid redundancy of tests).
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

import schemapack
from schemapack._internals.cli import cli
from schemapack._internals.dump import dumps_schemapack
from schemapack._internals.load import load_schemapack
from schemapack.cli import exit_codes
from tests.fixtures.examples import (
    INVALID_DATAPACK_PATHS,
    INVALID_SCHEMAPACK_PATHS,
    VALID_DATAPACK_PATHS,
    VALID_SCHEMAPACK_PATHS,
)

runner = CliRunner(
    mix_stderr=False,
)


def test_version():
    """Test the version command."""
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == exit_codes.SUCCESS == 0
    assert result.stdout.strip() == str(schemapack.__version__)


def generate_validate_command(
    *, schemapack: Path, datapack: Path, abbreviate: bool
) -> list[str]:
    """Generate a command line to validate a datapack against a schemapack."""
    return [
        "validate",
        "-s" if abbreviate else "--schemapack",
        str(schemapack),
        "-d" if abbreviate else "--datapack",
        str(datapack),
    ]


@pytest.mark.parametrize(
    "abbreviate", [True, False], ids=["abbreviate", "no_abbreviate"]
)
def test_validate_valid(abbreviate: bool):
    """Test the validate command with a valid datapack."""
    schemapack = VALID_SCHEMAPACK_PATHS["simple_relations"]
    datapack = VALID_DATAPACK_PATHS["simple_relations.simple_resources"]

    result = runner.invoke(
        cli,
        generate_validate_command(
            schemapack=schemapack, datapack=datapack, abbreviate=abbreviate
        ),
    )
    assert result.exit_code == exit_codes.SUCCESS == 0


@pytest.mark.parametrize(
    "abbreviate", [True, False], ids=["abbreviate", "no_abbreviate"]
)
def test_validate_invalid(abbreviate: bool):
    """Test the validate command with an invalid datapack."""
    schemapack = VALID_SCHEMAPACK_PATHS["simple_relations"]
    datapack = INVALID_DATAPACK_PATHS[
        "simple_relations.ContentValidationError.missing_property"
    ]

    result = runner.invoke(
        cli,
        generate_validate_command(
            schemapack=schemapack, datapack=datapack, abbreviate=abbreviate
        ),
    )
    assert result.exit_code == exit_codes.VALIDATION_ERROR != 0
    assert "ContentValidationError" in result.stderr


@pytest.mark.parametrize(
    "abbreviate", [True, False], ids=["abbreviate", "no_abbreviate"]
)
def test_validate_datapack_spec_error(abbreviate: bool):
    """Test the validate command with a datapack that does not comply with the specs."""
    schemapack = VALID_SCHEMAPACK_PATHS["simple_relations"]
    datapack = INVALID_DATAPACK_PATHS[
        "simple_relations.DataPackSpecError.DuplicateTargetIdError"
    ]

    result = runner.invoke(
        cli,
        generate_validate_command(
            schemapack=schemapack, datapack=datapack, abbreviate=abbreviate
        ),
    )
    assert result.exit_code == exit_codes.DATAPACK_SPEC_ERROR != 0
    assert "DataPackSpecError" in result.stderr


@pytest.mark.parametrize(
    "abbreviate", [True, False], ids=["abbreviate", "no_abbreviate"]
)
def test_validate_schemapack_spec_error(abbreviate: bool):
    """Test the validate command with a schemapack that does not comply with the specs."""
    schemapack = INVALID_SCHEMAPACK_PATHS["ContentSchemaNotFoundError"]
    datapack = VALID_DATAPACK_PATHS["simple_relations.simple_resources"]

    result = runner.invoke(
        cli,
        generate_validate_command(
            schemapack=schemapack, datapack=datapack, abbreviate=abbreviate
        ),
    )
    assert result.exit_code == exit_codes.SCHEMAPACK_SPEC_ERROR != 0
    assert "SchemaPackSpecError" in result.stderr


def test_check_schemapack_complies():
    """Test the check-schemapack command with a complies document."""
    schemapack = VALID_SCHEMAPACK_PATHS["simple_relations"]

    result = runner.invoke(cli, ["check-schemapack", str(schemapack)])
    assert result.exit_code == exit_codes.SUCCESS == 0


def test_check_schemapack_not_complies():
    """Test the check-schemapack command with a non compliant document."""
    schemapack = INVALID_SCHEMAPACK_PATHS["ContentSchemaNotFoundError"]

    result = runner.invoke(cli, ["check-schemapack", str(schemapack)])
    assert result.exit_code == exit_codes.SCHEMAPACK_SPEC_ERROR != 0
    assert "SchemaPackSpecError" in result.stderr


def test_check_datapack_complies():
    """Test the check-datapack command with a complies document."""
    datapack = VALID_DATAPACK_PATHS["simple_relations.simple_resources"]

    result = runner.invoke(cli, ["check-datapack", str(datapack)])
    assert result.exit_code == exit_codes.SUCCESS == 0


def test_check_datapack_not_complies():
    """Test the check-datapack command with a non compliant document."""
    datapack = INVALID_DATAPACK_PATHS[
        "simple_relations.DataPackSpecError.DuplicateTargetIdError"
    ]

    result = runner.invoke(cli, ["check-datapack", str(datapack)])
    assert result.exit_code == exit_codes.DATAPACK_SPEC_ERROR != 0
    assert "DataPackSpecError" in result.stderr


@pytest.mark.parametrize(
    "json, abbreviate",
    [(False, False), (True, False), (True, True)],
    ids=["yaml_format", "json_format_no_abbrev", "json_format_abbrev"],
)
def test_condense_schemapack(json: bool, abbreviate: bool):
    """Test the condense-schemapack command. This is checked against the output of
    the dumps_schemapack function. Further behavior is checked for that function.
    """
    schemapack_path = VALID_SCHEMAPACK_PATHS["simple_relations"]
    schemapack = load_schemapack(schemapack_path)
    expected_str = dumps_schemapack(schemapack, yaml_format=not json)

    command = ["condense-schemapack", str(schemapack_path)]
    if json:
        command.append("-j" if abbreviate else "--json")
    result = runner.invoke(cli, command)
    assert result.exit_code == exit_codes.SUCCESS == 0

    assert result.output.strip() == expected_str
