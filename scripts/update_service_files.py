#!/usr/bin/env python3

# Copyright 2021 - 2026 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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
"""A CLI tool to aid in running scripts."""

import io
from collections.abc import Callable
from contextlib import contextmanager, nullcontext, redirect_stdout
from functools import wraps

import typer

from script_utils import cli, utils
from update_config_docs import main as update_config
from update_openapi_docs import main as update_openapi

PREV_LINE = "\033[F\033[2K\r"  # moves up one line in the cli
REPORT_WIDTH = 35
app = typer.Typer(no_args_is_help=True, add_completion=False)


ServiceArg = typer.Argument(
    default="",
    case_sensitive=False,
    callback=utils.validate_folder_name,
)

CheckFlag = typer.Option(False, "--check")


@contextmanager
def suppress_print(service: str):
    """Temporarily suppress print statements."""
    try:
        with redirect_stdout(io.StringIO()):
            yield
    except Exception as e:
        cli.echo_warning(f"Unable to complete for '{service}'. See error below:")
        cli.echo_failure(str(e))
        exit(1)


def service_specific(func: Callable) -> Callable:
    """
    A decorator that runs the decorated function for all services if the service
    argument is an empty string, or runs it for the specified service otherwise.
    """

    @wraps(func)
    def wrapper(service: str = ServiceArg, *args, **kwargs):
        all_services = utils.list_service_dirs()
        service_count = len(all_services)
        check = kwargs.get("check", False)
        status = "Checking" if check else "Updating"
        func_name = func.__name__.replace("_", " ")
        line_prefix = PREV_LINE + PREV_LINE if check else PREV_LINE
        report = "Already up to date!" if check else "Done"

        if service == "":
            print(f"( ) {status} {func_name}...(1/{service_count})")

            for i, svc in enumerate(all_services):
                print(
                    f"{PREV_LINE}( ) {status} {func_name}...({i + 1}/{service_count}): {
                        svc.name
                    }",
                )
                with suppress_print(svc.name) if not check else nullcontext():
                    func(svc.name, *args, **kwargs)
                if check and i < service_count - 1:
                    print(PREV_LINE + PREV_LINE)

            cli.echo_success(
                f"{line_prefix}(✓) {status} {func_name}...({service_count}/{
                    service_count
                }): {report}"
            )

        else:
            print(f"( ) {status} {func_name} for {service}...")
            func(service, *args, **kwargs)
            cli.echo_success(
                f"{PREV_LINE}{PREV_LINE}(✓) {status} {func_name} for {service}... {
                    report
                }"
            )

    return wrapper


@app.command(name="config")
@service_specific
def config_docs(service: str = ServiceArg, check: bool = CheckFlag):
    """Update the config docs for one or all services (scripts/update_config_docs.py)."""
    update_config(service=service, check=check)


@app.command(name="openapi")
@service_specific
def openapi_docs(service: str = ServiceArg, check: bool = CheckFlag):
    """Update the OpenAPI docs for one or all services (scripts/update_openapi_docs.py)."""
    update_openapi(service=service, check=check)


@app.command(name="all-for")
def update_service_specific(service: str = ServiceArg, check: bool = CheckFlag):
    """Run all *service-specific* update scripts for one or all services, in order."""
    print(f"Running all scripts for {service if service else 'all services'}.")
    config_docs(service=service, check=check)
    openapi_docs(service=service, check=check)


@app.command(name="all")
def update_all(check: bool = CheckFlag):
    """Run all update scripts for everything in order.

    Scripts are run in order to account for downstream changes, such as config -> readme.
    Service-specific scripts are run for all services.
    """
    config_docs(service="", check=check)
    openapi_docs(service="", check=check)


if __name__ == "__main__":
    app()
