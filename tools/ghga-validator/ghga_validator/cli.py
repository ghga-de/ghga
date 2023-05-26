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

from ghga_validator.core.validation import get_target_class, validate
from ghga_validator.plugins import GHGAJsonSchemaValidationPlugin, RefValidationPlugin

cli = typer.Typer()

VALIDATION_PLUGINS = [
    {"plugin_class": RefValidationPlugin},
    {"plugin_class": GHGAJsonSchemaValidationPlugin},
]


def validate_json(file: Path, schema: Path, report: Path, target_class: str) -> bool:
    """
    Validate JSON object against a given schema. Store the errors to the validation report.
    Args:
        file: The URL or path to submission file
        schema: The URL or path to YAML file (submission schema)
        report: The URL or path to store the validation results
    """
    with open(file, "r", encoding="utf8") as json_file:
        submission_json = json.load(json_file)
    if submission_json is None:
        raise EOFError(f"<{file}> is empty! Nothing to validate!")
    validation_report = validate(
        str(Path(schema).resolve()),
        target_class=target_class,
        obj=submission_json,
        plugins=VALIDATION_PLUGINS,
    )
    with open(report, "w", encoding="utf-8") as sub:
        json.dump(
            validation_report.dict(exclude_unset=True, exclude_none=True),
            sub,
            ensure_ascii=False,
            indent=4,
        )
    return validation_report.valid


@cli.command()
def main(
    schema: Path = typer.Option(
        ..., help="Path to metadata schema (modelled using LinkML)"
    ),
    inputfile: Path = typer.Option(
        ..., help="Path to submission file in JSON format to be validated"
    ),
    report: Path = typer.Option(..., help="Path to resulting validation report"),
    target_class: Optional[str] = typer.Option(None, help="The root class name"),
):
    """
    GHGA Validator
    """
    typer.echo("Start validating...")
    if not target_class:
        target_class = get_target_class(str(Path(schema).resolve()))
    if not target_class:
        raise TypeError(
            "Target class cannot be inferred,"
            + "please specify the 'target_class' argument"
        )
    if validate_json(inputfile, schema, report, target_class):
        typer.echo(f"<{inputfile}> is valid!")
    else:
        typer.echo(
            f"<{inputfile}> is invalid! Look at <{report}> for validation report"
        )
