# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
"""CLI-specific wrappers around core functions."""

from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer

from . import __version__, transpiler_io
from .transpile import transpile

cli = typer.Typer()


def version_callback(value: bool):
    """Prints the package version"""
    if value:
        print(__version__)
        raise typer.Exit()


def format_callback(value: str):
    """Validates the user input for format parameter"""
    if value not in ["json", "yaml"]:
        raise typer.BadParameter("Only 'json' or 'yaml' is allowed.")
    return value


class Format(str, Enum):
    """Enum class for output format types"""

    json = "json"
    yaml = "yaml"


@cli.command()
def main(
    spread_sheet: Annotated[
        Path,
        typer.Argument(
            exists=True,
            help="The path to input file (XLSX)",
            dir_okay=False,
            readable=True,
        ),
    ],
    output_file: Annotated[
        Path | None,
        typer.Argument(help="The path to output file (JSON).", dir_okay=False),
    ] = None,
    format: Annotated[
        Format,
        typer.Option(
            "--format",
            "-t",
            help="Output format: 'json' or 'yaml'",
            callback=format_callback,
            is_eager=True,
        ),
    ] = Format.json,
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Override output file if it exists.")
    ] = False,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Print package version",
        ),
    ] = False,
):
    """ghga-transpiler is a command line utility to transpile the official GHGA
    metadata XLSX workbooks to JSON. TODO Validation
    """
    try:
        ghga_datapack = transpile(spread_sheet)
    except SyntaxError as exc:
        sys.exit(f"Unable to parse input file '{spread_sheet}': {exc}")
    yaml_format = format == "yaml"
    try:
        transpiler_io.write_datapack(
            data=ghga_datapack, path=output_file, yaml_format=yaml_format, force=force
        )
    except FileExistsError as exc:
        sys.exit(f"ERROR: {exc}")
