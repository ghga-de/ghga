# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
import ruamel.yaml
from typer.testing import CliRunner

from schemapack import __version__ as schemapack_version
from schemapack._internals.cli import cli
from schemapack._internals.utils import read_json_or_yaml_mapping
from schemapack.cli import exit_codes
from tests.fixtures.examples import (
    ERD_PATHS,
    INVALID_DATAPACK_PATHS,
    INVALID_SCHEMAPACK_PATHS,
    VALID_DATAPACK_PATHS,
    VALID_SCHEMAPACK_PATHS,
)
from tests.fixtures.utils import (
    assert_formatted_string,
    loads_json_or_yaml_mapping,
    strip_ansi_escape_sequences,
)

yaml = ruamel.yaml.YAML(typ="rt")
runner = CliRunner()


def test_version():
    """Test the version command."""
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == exit_codes.SUCCESS == 0
    assert strip_ansi_escape_sequences(result.stdout).strip() == str(schemapack_version)


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
    "json_format, abbreviate",
    [(False, False), (True, False), (True, True)],
    ids=["yaml", "json", "json_abbrev"],
)
def test_condense_schemapack(json_format: bool, abbreviate: bool):
    """Test the condense-schemapack command."""
    schemapack_path = VALID_SCHEMAPACK_PATHS["simple_relations"]
    expected_dict = read_json_or_yaml_mapping(
        VALID_SCHEMAPACK_PATHS["simple_relations_condensed"]
    )

    command = ["condense-schemapack", str(schemapack_path)]
    if json_format:
        command.append("-j" if abbreviate else "--json")
    result = runner.invoke(cli, command)
    assert result.exit_code == exit_codes.SUCCESS == 0

    observed_str = strip_ansi_escape_sequences(result.stdout)
    assert_formatted_string(observed_str, json_format=json_format)

    observed_dict = loads_json_or_yaml_mapping(observed_str)
    assert observed_dict == expected_dict


@pytest.mark.parametrize(
    "json_format, abbreviate",
    [(False, False), (True, False), (True, True)],
    ids=["yaml", "json", "json_abbrev"],
)
def test_isolate_resource(json_format: bool, abbreviate: bool):
    """Test the isolate_resource command."""
    schemapack_path = VALID_SCHEMAPACK_PATHS["simple_relations"]
    datapack_path = VALID_DATAPACK_PATHS["simple_relations.simple_resources"]
    expected_dict = read_json_or_yaml_mapping(
        VALID_DATAPACK_PATHS["simple_relations_rooted.rooted_simple_resources"]
    )
    class_name = "Dataset"
    resource_id = "example_dataset_1"

    command = [
        "isolate-resource",
        "-s" if abbreviate else "--schemapack",
        str(schemapack_path),
        "-d" if abbreviate else "--datapack",
        str(datapack_path),
        "-c" if abbreviate else "--class-name",
        class_name,
        "-r" if abbreviate else "--resource-id",
        resource_id,
    ]
    if json_format:
        command.append("-j" if abbreviate else "--json")
    result = runner.invoke(cli, command)
    assert result.exit_code == exit_codes.SUCCESS == 0

    observed_str = strip_ansi_escape_sequences(result.output)
    assert_formatted_string(observed_str, json_format=json_format)

    observed_dict = loads_json_or_yaml_mapping(observed_str)
    assert observed_dict == expected_dict


def test_isolate_resource_non_existing_class():
    """Test the isolate_resource command with a non-existing class."""
    schemapack_path = VALID_SCHEMAPACK_PATHS["simple_relations"]
    datapack_path = VALID_DATAPACK_PATHS["simple_relations.simple_resources"]
    class_name = "NonExistingClass"
    resource_id = "example_dataset_1"

    command = [
        "isolate-resource",
        "--schemapack",
        str(schemapack_path),
        "--datapack",
        str(datapack_path),
        "--class-name",
        class_name,
        "--resource-id",
        resource_id,
    ]
    result = runner.invoke(cli, command)
    assert result.exit_code == exit_codes.CLASS_NOT_FOUND_ERROR != 0
    assert "ClassNotFoundError" in result.stderr


def test_isolate_resource_non_existing_resource():
    """Test the isolate_resource command with a non-existing resource."""
    schemapack_path = VALID_SCHEMAPACK_PATHS["simple_relations"]
    datapack_path = VALID_DATAPACK_PATHS["simple_relations.simple_resources"]
    class_name = "Dataset"
    resource_id = "non_existing_resource"

    command = [
        "isolate-resource",
        "--schemapack",
        str(schemapack_path),
        "--datapack",
        str(datapack_path),
        "--class-name",
        class_name,
        "--resource-id",
        resource_id,
    ]
    result = runner.invoke(cli, command)
    assert result.exit_code == exit_codes.RESOURCE_NOT_FOUND_ERROR != 0
    assert "ResourceNotFoundError" in result.stderr


@pytest.mark.parametrize(
    "json_format, abbreviate",
    [(False, False), (True, False), (True, True)],
    ids=["yaml", "json", "json_abbrev"],
)
def test_isolate_class(json_format: bool, abbreviate: bool):
    """Test the isolate_class command."""
    schemapack_path = VALID_SCHEMAPACK_PATHS["simple_relations"]
    expected_dict = read_json_or_yaml_mapping(
        VALID_SCHEMAPACK_PATHS["simple_relations_rooted_condensed"]
    )
    class_name = "Dataset"

    command = [
        "isolate-class",
        "-s" if abbreviate else "--schemapack",
        str(schemapack_path),
        "-c" if abbreviate else "--class-name",
        class_name,
    ]
    if json_format:
        command.append("-j" if abbreviate else "--json")
    result = runner.invoke(cli, command)
    assert result.exit_code == exit_codes.SUCCESS == 0

    observed_str = strip_ansi_escape_sequences(result.output)
    assert_formatted_string(observed_str, json_format=json_format)

    observed_dict = loads_json_or_yaml_mapping(observed_str)
    assert observed_dict == expected_dict


def test_isolate_class_non_existing():
    """Test the isolate_class command with a non-existing class."""
    schemapack_path = VALID_SCHEMAPACK_PATHS["simple_relations"]
    class_name = "NonExistingClass"

    command = [
        "isolate-class",
        "--schemapack",
        str(schemapack_path),
        "--class-name",
        class_name,
    ]
    result = runner.invoke(cli, command)
    assert result.exit_code == exit_codes.CLASS_NOT_FOUND_ERROR != 0
    assert "ClassNotFoundError" in result.stderr


@pytest.mark.parametrize(
    "props,example_suffix",
    [
        ([], "_wo_props"),
        (["-c"], "_w_props"),
        (["--content-properties"], "_w_props"),
    ],
    ids=("no_content_props", "content_props_abbrev", "content_props"),
)
def test_export_mermaid(tmp_path, props: list[str], example_suffix: str):
    """Test the export-mermaid command."""
    example = "comprehensive_cardinalities_and_types"
    schemapack = VALID_SCHEMAPACK_PATHS[example]
    erd = ERD_PATHS[example + example_suffix]

    args = [
        "export-mermaid",
        str(schemapack),
        *props,
    ]
    result = runner.invoke(cli, args)
    assert result.exit_code == exit_codes.SUCCESS == 0
    assert strip_ansi_escape_sequences(result.output) == erd.read_text()
