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
""" CLI-specific wrappers around core functions."""
import sys
from pathlib import Path
from typing import Optional

import typer

from ghga_transpiler import io

from .config.exceptions import MissingWorkbookContent, UnknownVersionError
from .core import convert_workbook

cli = typer.Typer()


@cli.command()
def cli_main(
    spread_sheet: Path = typer.Argument(
        ...,
        exists=True,
        help="The path to input file",
        dir_okay=False,
        readable=True,
    ),
    output_file: Optional[Path] = typer.Argument(
        None, help="The path to output file.", dir_okay=False
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Override output file if it exists."
    ),
):
    """Function to get options and channel those to the convert workbook functionality"""
    try:
        ghga_workbook = io.read_workbook(spread_sheet)
    except (SyntaxError, UnknownVersionError) as exc:
        sys.exit(f"Unable to parse input file '{spread_sheet}': {exc}")

    try:
        converted = convert_workbook(ghga_workbook)
    except MissingWorkbookContent as exc:
        sys.exit(f"Unable to convert the input file '{spread_sheet}': {exc}")

    try:
        io.write_json(data=converted, path=output_file, force=force)
    except FileExistsError as exc:
        sys.exit(f"ERROR: {exc}")
