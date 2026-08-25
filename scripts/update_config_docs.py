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

"""Generates a JSON schema from the service's Config class as well as a corresponding
example config yaml (or check whether these files are up to date).
"""

import importlib
import json
import sys
from contextlib import contextmanager
from difflib import unified_diff
from pathlib import Path
from typing import Any

import yaml

from get_package_name import get_package_name
from script_utils.cli import echo_failure, echo_success, run

HERE = Path(__file__).parent.resolve()
REPO_ROOT_DIR = HERE.parent
SERVICES_DIR = REPO_ROOT_DIR / "services"
GET_PACKAGE_NAME_SCRIPT = HERE / "get_package_name.py"

dev_config_yaml = REPO_ROOT_DIR / ".devcontainer" / ".dev_config.yaml"
config_schema_json = REPO_ROOT_DIR / "config_schema.json"
example_config_yaml = REPO_ROOT_DIR / "example_config.yaml"


class ValidationError(RuntimeError):
    """Raised when validation of config documentation fails."""


@contextmanager
def set_service_specific_vars(service: str):
    """Adjust global vars for service."""
    global dev_config_yaml, config_schema_json, example_config_yaml

    # verify that the folder exists
    service_dir = SERVICES_DIR / service
    if not service_dir.exists():
        echo_failure(f"{service_dir} does not exist")
        exit(1)

    # set the vars
    dev_config_yaml = service_dir / "dev_config.yaml"
    config_schema_json = service_dir / "config_schema.json"
    example_config_yaml = service_dir / "example_config.yaml"

    yield

    # reset the vars
    dev_config_yaml = REPO_ROOT_DIR / ".devcontainer" / ".dev_config.yaml"
    config_schema_json = REPO_ROOT_DIR / "config_schema.json"
    example_config_yaml = REPO_ROOT_DIR / "example_config.yaml"


def get_config_class(service: str):
    """
    Dynamically imports and returns the Config class from the current service.
    This makes the script service repo agnostic.
    """
    package_name = get_package_name(service)
    config_module: Any = importlib.import_module(f"{package_name}.config")

    return config_module.Config


def get_dev_config(service: str):
    """Get dev config object."""
    config_class = get_config_class(service)
    return config_class(config_yaml=dev_config_yaml)


def get_schema(service: str) -> str:
    """Returns a JSON schema generated from a Config class."""

    config = get_dev_config(service)
    return config.schema_json(indent=2)  # change eventually to .model_json_schema(...)


def get_example(service: str) -> str:
    """Returns an example config YAML."""

    config = get_dev_config(service)
    normalized_config_dict = json.loads(
        config.json()  # change eventually to .model_dump_json()
    )
    return yaml.dump(normalized_config_dict)  # pyright: ignore


def update_docs(service: str):
    """Update the example config and config schema files documenting the config
    options."""

    example = get_example(service)
    with open(example_config_yaml, "w", encoding="utf-8") as example_file:
        example_file.write(example)

    schema = get_schema(service)
    with open(config_schema_json, "w", encoding="utf-8") as schema_file:
        schema_file.write(schema)


def print_diff(expected: str, observed: str):
    """Print differences between expected and observed files."""
    echo_failure("Differences in Config YAML:")
    for line in unified_diff(
        expected.splitlines(keepends=True),
        observed.splitlines(keepends=True),
        fromfile="expected",
        tofile="observed",
    ):
        print("   ", line.rstrip())


def check_docs(service: str):
    """Check whether the example config and config schema files documenting the config
    options are up to date.

    Raises:
        ValidationError: if not up to date.
    """

    example_expected = get_example(service)
    with open(example_config_yaml, encoding="utf-8") as example_file:
        example_observed = example_file.read()
    if example_expected != example_observed:
        print_diff(example_expected, example_observed)
        raise ValidationError(
            f"Example config YAML at '{example_config_yaml}' is not up to date."
        )

    schema_expected = get_schema(service)
    with open(config_schema_json, encoding="utf-8") as schema_file:
        schema_observed = schema_file.read()
    if schema_expected != schema_observed:
        raise ValidationError(
            f"Config schema JSON at '{config_schema_json}' is not up to date."
        )


def main(*, service: str, check: bool = False):
    """Update or check the config documentation files."""
    with set_service_specific_vars(service):
        if check:
            try:
                check_docs(service)
            except ValidationError as error:
                echo_failure(f"Validation failed: {error}")
                sys.exit(1)
            echo_success(f"Config docs for {service} are up to date.")
            return

        update_docs(service)
        echo_success(f"Successfully updated the config docs for {service}.")


if __name__ == "__main__":
    run(main)
