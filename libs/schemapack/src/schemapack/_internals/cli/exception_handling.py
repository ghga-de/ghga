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

"""Handling user-derived exceptions in the CLI."""

from contextlib import contextmanager

import typer

from schemapack import exceptions
from schemapack._internals.cli import exit_codes
from schemapack._internals.cli.printing import print_exception, print_final_failure


@contextmanager
def expect_validation_errors():
    """Handle validation errors."""
    try:
        yield
    except exceptions.ValidationError as error:
        print_exception(error, exception_name="ValidationError")
        print_final_failure(
            "The provided datapack is not valid wrt the provided schemapack.",
        )
        raise typer.Exit(exit_codes.VALIDATION_ERROR) from None


@contextmanager
def expect_datapackspec_errors():
    """Handle datapackspec errors."""
    try:
        yield
    except exceptions.DataPackSpecError as error:
        print_exception(error, exception_name="DataPackSpecError")
        print_final_failure(
            "The provided document did not comply with the specs of a datapack."
        )
        raise typer.Exit(exit_codes.DATAPACK_SPEC_ERROR) from None


@contextmanager
def expect_schemapack_errors():
    """Handle schemapack errors."""
    try:
        yield
    except exceptions.SchemaPackSpecError as error:
        print_exception(error, exception_name="SchemaPackSpecError")
        print_final_failure(
            "The provided document did not comply with the specs of a schemapack."
        )
        raise typer.Exit(exit_codes.SCHEMAPACK_SPEC_ERROR) from None


@contextmanager
def expect_common_user_errors():
    """Handle all user-derived errors."""
    with (
        expect_validation_errors(),
        expect_datapackspec_errors(),
        expect_schemapack_errors(),
    ):
        yield


@contextmanager
def expect_class_not_found_errors():
    """Handle class not found errors."""
    try:
        yield
    except exceptions.ClassNotFoundError as error:
        print_exception(error, exception_name="ClassNotFoundError")
        print_final_failure(
            "The provided document did not contain the specified class."
        )
        raise typer.Exit(exit_codes.CLASS_NOT_FOUND_ERROR) from None


@contextmanager
def expect_resource_not_found_errors():
    """Handle resource not found errors."""
    try:
        yield
    except exceptions.ResourceNotFoundError as error:
        print_exception(error, exception_name="ResourceNotFoundError")
        print_final_failure(
            "The provided document did not contain the specified resource."
        )
        raise typer.Exit(exit_codes.RESOURCE_NOT_FOUND_ERROR) from None


@contextmanager
def expect_class_or_resource_not_found_errors():
    """Handle class or resource not found errors."""
    with expect_class_not_found_errors(), expect_resource_not_found_errors():
        yield
