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

"""Describes a command line interface"""

from pathlib import Path
from typing import Annotated

import typer

from schemapack import __version__
from schemapack._internals.cli import exit_codes
from schemapack._internals.cli.exception_handling import (
    expect_datapackspec_errors,
    expect_schemapack_errors,
    expect_user_errors,
)
from schemapack._internals.cli.printing import print_final_success, print_info
from schemapack._internals.load import load_datapack, load_schemapack
from schemapack._internals.main import load_and_validate

cli = typer.Typer()


def version_callback(
    version: bool = False,
):
    if version:
        print_info(__version__)
        raise typer.Exit(exit_codes.SUCCESS)


@cli.callback()
def common(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=version_callback,
            help="Show the version of the library and exit.",
        ),
    ] = False,
):
    """Common arguments and options."""
    pass


@cli.command()
def validate(
    *,
    schemapack: Annotated[
        Path,
        typer.Option(
            "--schemapack",
            "-s",
            help="Provide the path to a schemapack to validate against.",
        ),
    ],
    datapack: Annotated[
        Path,
        typer.Option(
            "--datapack", "-d", help="Provide the path to a datapack to validate."
        ),
    ],
):
    """Validate a datapack against a schemapack."""
    with expect_user_errors():
        load_and_validate(schemapack_path=schemapack, datapack_path=datapack)

    print_final_success("The provided datapack is valid wrt the provided schemapack.")


@cli.command()
def check_schemapack(
    *,
    schemapack: Annotated[
        Path,
        typer.Argument(
            help="Provide the path to a JSON/YAML file to check against the specs.",
        ),
    ],
):
    """Check if the provided JSON/YAML document complies with the schemapack specs."""
    with expect_schemapack_errors():
        load_schemapack(schemapack)

    print_final_success(
        "The provided document complies with the specs of a schemapack."
    )


@cli.command()
def check_datapack(
    *,
    datapack: Annotated[
        Path,
        typer.Argument(
            help="Provide the path to a JSON/YAML file to check against the specs.",
        ),
    ],
):
    """Check if the provided JSON/YAML document complies with the datapack specs."""
    with expect_datapackspec_errors():
        load_datapack(datapack)

    print_final_success("The provided document complies with the specs of a datapack.")
