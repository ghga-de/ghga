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
#

"""Entrypoint of the package"""

import json
from pathlib import Path
from typing import Optional

import typer
import yaml
from linkml_runtime.utils.schemaview import SchemaView

from ghga_validator.core.models import ValidationReport
from ghga_validator.core.validator import Validator
from ghga_validator.plugins.base_plugin import ValidationPlugin
from ghga_validator.plugins.utils import discover_plugins
from ghga_validator.schema_utils import get_target_class

cli = typer.Typer()

DEFAULT_PLUGINS = ["GHGAJsonSchemaValidationPlugin"]

VALIDATION_PLUGINS = ["RefValidationPlugin", "UniqueIdentifierValidationPlugin"]


def validate_json_file(
    file: Path, schema: Path, report: Path, target_class: str
) -> bool:
    """
    Validate JSON object read from a file against a given schema.
    Store the errors to the validation report.
    Args:
        file: The URL or path to file containing data to be validated
        schema: The URL or path to YAML file
        report: The URL or path to store the validation results
    """
    with open(file, encoding="utf8") as json_file:
        submission_json = yaml.safe_load(json_file)
    if submission_json is None:
        raise EOFError(f"<{file}> is empty! Nothing to validate!")
    schema_view = SchemaView(schema)
    validation_report = validate(
        schema_view,
        target_class=target_class,
        data=submission_json,
        plugins=load_plugins(DEFAULT_PLUGINS, schema_view),
    )
    if validation_report.valid:
        default_validation_results = validation_report.validation_results
        validation_report = validate(
            schema_view,
            target_class=target_class,
            data=submission_json,
            plugins=load_plugins(VALIDATION_PLUGINS, schema_view),
        )
        validation_report.validation_results = (
            default_validation_results + validation_report.validation_results
        )
    else:
        typer.echo(
            "JSON schema validation failed. Subsequent validations skipped.", err=True
        )

    with open(report, "w", encoding="utf-8") as sub:
        json.dump(
            validation_report.dict(
                exclude={"object"}, exclude_unset=True, exclude_none=True
            ),
            sub,
            ensure_ascii=False,
            indent=4,
        )
    return validation_report.valid


def validate(
    schema: SchemaView,
    target_class: str,
    data: dict,
    plugins: list,
) -> ValidationReport:
    """
    Validate an object of a particular type against a given schema.
    Args:
        schema: Virtual LinkML schema (SchemaView)
        target_class: The root class name
        data: The JSON object to validate
        plugins: List of plugin class names for validation
    """
    validator = Validator(schema=schema, plugins=plugins)
    report = validator.validate(data, target_class)
    return report


def load_plugins(plugin_types: list[str], schema: SchemaView) -> list[ValidationPlugin]:
    """Load the list of plugins"""
    plugin_list = []
    discovered_plugins = discover_plugins(ValidationPlugin)
    for plugin_name in plugin_types:
        if plugin_name in discovered_plugins:
            plugin_class = discovered_plugins[plugin_name]
            plugin_list.append(plugin_class(schema=schema))
        else:
            raise ModuleNotFoundError(f"Plugin '{plugin_name}' not found")
    return plugin_list


@cli.command()
def main(
    schema: Path = typer.Option(
        ..., "--schema", "-s", help="Path to metadata schema (modelled using LinkML)"
    ),
    input_file: Path = typer.Option(
        ...,
        "--input",
        "-i",
        file_okay=True,
        dir_okay=False,
        help="Path to submission file in JSON format to be validated",
    ),
    report: Path = typer.Option(
        ...,
        "--report",
        "-r",
        file_okay=True,
        dir_okay=False,
        writable=True,
        help="Path to resulting validation report",
    ),
    target_class: Optional[str] = typer.Option(None, help="The root class name"),
):
    """
    GHGA Validator

    ghga-validator is a command line utility to validate metadata w.r.t. its
    compliance to the GHGA Metadata Model. It takes metadata encoded in JSON of
    YAML format and produces a validation report in JSON format.
    """
    typer.echo("Start validating...")
    if not target_class:
        target_class = get_target_class(str(Path(schema).resolve()))
    if not target_class:
        raise TypeError(
            "Target class cannot be inferred,"
            + "please specify the 'target_class' argument"
        )
    if validate_json_file(input_file, schema, report, target_class):
        typer.echo(f"<{input_file}> is valid!")
    else:
        typer.echo(
            f"<{input_file}> is invalid! Look at <{report}> for validation report"
        )
