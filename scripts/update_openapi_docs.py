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

"""Updates OpenAPI-based documentation"""

import json
import subprocess
import sys
from contextlib import contextmanager
from difflib import unified_diff
from pathlib import Path

import yaml

from script_utils.cli import echo_failure, echo_success, echo_warning, run

HERE = Path(__file__).parent.resolve()
REPO_ROOT_DIR = HERE.parent
SERVICES_DIR = REPO_ROOT_DIR / "services"

openapi_yaml = REPO_ROOT_DIR / "openapi.yaml"
app_openapi_script = REPO_ROOT_DIR / "app_openapi.py"


class ValidationError(RuntimeError):
    """Raised when validation of OpenAPI documentation fails."""


@contextmanager
def set_service_specific_vars(service: str):
    """Adjust global vars for service."""
    global openapi_yaml, app_openapi_script

    # verify that the folder exists
    service_dir = SERVICES_DIR / service
    if not service_dir.exists():
        echo_failure(f"{service_dir} does not exist")
        exit(1)

    # set the vars
    openapi_yaml = service_dir / "openapi.yaml"
    app_openapi_script = service_dir / "scripts" / "app_openapi.py"

    yield

    # reset the vars
    openapi_yaml = REPO_ROOT_DIR / "openapi.yaml"
    app_openapi_script = REPO_ROOT_DIR / "app_openapi.py"


def get_openapi_spec() -> str:
    """Get an OpenAPI spec in YAML format from the main FastAPI app as defined in the
    service's app_openapi.py file.
    """

    with subprocess.Popen(
        args=[app_openapi_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    ) as process:
        # communicate() rather than wait(), which deadlocks as soon as the spec
        # exceeds the OS pipe buffer
        raw_openapi, _ = process.communicate()
        if process.returncode != 0:
            raise ValidationError("Failed to get openapi from file.")

    openapi_spec = json.loads(raw_openapi.decode("utf-8").strip("\n"))
    return yaml.safe_dump(openapi_spec)


def update_docs():
    """Update the OpenAPI YAML file located in the service's dir."""

    openapi_spec = get_openapi_spec()
    with open(openapi_yaml, "w", encoding="utf-8") as openapi_file:
        openapi_file.write(openapi_spec)


def print_diff(expected: str, observed: str):
    """Print differences between expected and observed files."""
    echo_failure("Differences in OpenAPI YAML:")
    for line in unified_diff(
        expected.splitlines(keepends=True),
        observed.splitlines(keepends=True),
        fromfile="expected",
        tofile="observed",
    ):
        print("   ", line.rstrip())


def check_docs():
    """Checks whether the OpenAPI YAML file located in the service's dir is up
    to date.

    Raises:
        ValidationError: if not up to date.
    """

    openapi_expected = get_openapi_spec()
    with open(openapi_yaml, encoding="utf-8") as openapi_file:
        openapi_observed = openapi_file.read()

    if openapi_expected != openapi_observed:
        print_diff(openapi_expected, openapi_observed)
        raise ValidationError(
            f"The OpenAPI YAML at '{openapi_yaml}' is not up to date."
        )


def main(*, service: str, check: bool = False):
    """Update or check the OpenAPI documentation."""
    with set_service_specific_vars(service):
        # only act on services that use openapi
        if not app_openapi_script.exists():
            relative_location = app_openapi_script.relative_to(SERVICES_DIR / service)
            echo_warning(f"{service}: skipping, {relative_location} not found")
            return

        if check:
            try:
                check_docs()
            except ValidationError as error:
                echo_failure(f"Validation failed: {error}")
                sys.exit(1)
            echo_success(f"{service}: OpenAPI docs are up to date.")
            return

        update_docs()
        echo_success(f"{service}: Successfully updated the OpenAPI docs.")


if __name__ == "__main__":
    run(main)
