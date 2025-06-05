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

"""Describes a command line interface"""

from pathlib import Path
from typing import Annotated

import typer

from schemapack import __version__
from schemapack._internals.cli import exit_codes
from schemapack._internals.cli.exception_handling import (
    expect_class_or_resource_not_found_errors,
    expect_common_user_errors,
    expect_datapackspec_errors,
    expect_schemapack_errors,
)
from schemapack._internals.cli.printing import (
    print_final_success,
    print_output,
)
from schemapack._internals.dump import dumps_datapack, dumps_schemapack
from schemapack._internals.erd import export_mermaid as export_mermaid_impl
from schemapack._internals.isolate import isolate_class as isolate_class_impl
from schemapack._internals.isolate import isolate_resource as isolate_resource_impl
from schemapack._internals.load import load_datapack, load_schemapack
from schemapack._internals.main import load_and_validate

cli = typer.Typer()


def version_callback(
    version: bool = False,
):
    if version:
        print_output(__version__)
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
    with expect_common_user_errors():
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


@cli.command()
def condense_schemapack(
    *,
    schemapack: Annotated[
        Path,
        typer.Argument(
            help="Provide the path to a JSON/YAML file to check against the specs.",
        ),
    ],
    json: Annotated[
        bool,
        typer.Option(
            "--json",
            "-j",
            help="Output the condensed schemapack as JSON instead of YAML.",
        ),
    ] = False,
):
    """Writes a condensed version of the provided schemapack that contains content
    schemas to stdout.
    """
    with expect_schemapack_errors():
        schemapack_dict = load_schemapack(schemapack)
        condensed_schemapack = dumps_schemapack(schemapack_dict, yaml_format=not json)
        print_output(condensed_schemapack)


@cli.command()
def isolate_resource(
    *,
    schemapack: Annotated[
        Path,
        typer.Option(
            "--schemapack",
            "-s",
            help=(
                "The path to a schemapack that describes the structure of the"
                " provided input datapack (not the rooted datapack output by this"
                " command)."
            ),
        ),
    ],
    datapack: Annotated[
        Path,
        typer.Option(
            "--datapack",
            "-d",
            help="The path to a datapack from which the resource shall be isolated.",
        ),
    ],
    class_name: Annotated[
        str,
        typer.Option(
            "--class-name",
            "-c",
            help="The name of the class of the resource to isolate.",
        ),
    ],
    resource_id: Annotated[
        str,
        typer.Option(
            "--resource-id",
            "-r",
            help="The ID of the resource to isolate.",
        ),
    ],
    json: Annotated[
        bool,
        typer.Option(
            "--json",
            "-j",
            help="Output the rooted datapack as JSON instead of YAML.",
        ),
    ] = False,
):
    """Isolate a resource from the given datapack and write a datapack that is rooted to
    this resource to stdout.
    """
    with expect_common_user_errors():
        schemapack_obj, datapack_obj = load_and_validate(
            schemapack_path=schemapack, datapack_path=datapack
        )

    with expect_class_or_resource_not_found_errors():
        rooted_datapack = isolate_resource_impl(
            datapack=datapack_obj,
            class_name=class_name,
            resource_id=resource_id,
            schemapack=schemapack_obj,
        )

    rooted_datapack_str = dumps_datapack(rooted_datapack, yaml_format=not json)
    print_output(rooted_datapack_str)


@cli.command()
def isolate_class(
    *,
    schemapack: Annotated[
        Path,
        typer.Option(
            "--schemapack",
            "-s",
            help=(
                "The path to a schemapack that describes the structure of the"
                " provided input datapack (not the rooted datapack output by this"
                " command)."
            ),
        ),
    ],
    class_name: Annotated[
        str,
        typer.Option(
            "--class-name",
            "-c",
            help="The name of the class of the resource to isolate.",
        ),
    ],
    json: Annotated[
        bool,
        typer.Option(
            "--json",
            "-j",
            help="Output the rooted datapack as JSON instead of YAML.",
        ),
    ] = False,
):
    """Isolate a class from the given schemapack and write a condensed (with content
    schemas being embedded) schemapack that is rooted to this class to stdout.
    """
    with expect_common_user_errors():
        schemapack_obj = load_schemapack(schemapack)

    with expect_class_or_resource_not_found_errors():
        rooted_schemapack = isolate_class_impl(
            schemapack=schemapack_obj,
            class_name=class_name,
        )

    rooted_schemapack_str = dumps_schemapack(rooted_schemapack, yaml_format=not json)
    print_output(rooted_schemapack_str)


@cli.command()
def export_mermaid(
    *,
    schemapack: Annotated[
        Path,
        typer.Argument(
            help="Provide the path to a schemapack file to export.",
        ),
    ],
    content_properties: Annotated[
        bool,
        typer.Option(
            "--content-properties",
            "-c",
            help="Include properties in the output.",
        ),
    ] = False,
):
    """Generate an entity relationship diagram based on the mermaid markup from the
    provided schemapack.
    """
    with expect_schemapack_errors():
        schemapack_ = load_schemapack(schemapack)

    erd_diagram = export_mermaid_impl(
        schemapack=schemapack_, content_properties=content_properties
    )
    print_output(erd_diagram)


#    print_final_success("Schemapack exported successfully.")
