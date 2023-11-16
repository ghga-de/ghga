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

"""Utility functions."""

import json
import os
from collections.abc import Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal

import jsonschema
import jsonschema.exceptions
import jsonschema.validators
import yaml
from jsonschema.protocols import Validator as JsonSchemaValidator


class DecodeError(ValueError):
    """Raised when decoding JSON or YAML data fails."""

    def __init__(self, path: Path, assumed_format: Literal["JSON", "YAML"]):
        super().__init__(
            f"The file at '{path}' could not be decoded assuming {assumed_format}"
            + " format."
        )
        self.path = path
        self.assumed_format = assumed_format


def read_json_or_yaml(path: Path) -> dict:
    """Read JSON or YAML data from file. The format is decided based on the file
    extension. If the file extension is not recognized, YAML is assumed (as it is a
    superset of JSON).

    Raises:
        DecodeError: If the file cannot be decoded as JSON or YAML.
    """
    with path.open("r", encoding="utf-8") as file:
        if path.suffix == ".json":
            try:
                data = json.load(file)
            except json.JSONDecodeError as error:
                raise DecodeError(
                    path=path,
                    assumed_format="JSON",
                ) from error
        else:
            # Even if the file ending does not indicate YAML, we try to parse it as YAML
            try:
                data = yaml.safe_load(file)
            except yaml.YAMLError as error:
                raise DecodeError(
                    path=path,
                    assumed_format="YAML",
                ) from error

        if not isinstance(data, dict):
            raise DecodeError(
                path=path,
                assumed_format="JSON",
            )

        return data


class JsonSchemaError(ValueError):
    """Raised when a JSON schema is invalid."""


def get_json_schema_validator(schema: Mapping[str, Any]) -> JsonSchemaValidator:
    """Get a JSON schema validator for the given schema.

    Raises:
        JsonSchemaError: If the schema is invalid.
    """
    cls = jsonschema.validators.validator_for(schema)

    try:
        cls.check_schema(schema)
    except jsonschema.exceptions.SchemaError as error:
        raise JsonSchemaError(error.message) from error

    return cls(schema)


@contextmanager
def transient_directory_change(path: Path):
    """Change the current working directory temporarily within a with block."""
    original_cwd = os.getcwd()
    os.chdir(path)

    try:
        yield
    finally:
        os.chdir(original_cwd)
