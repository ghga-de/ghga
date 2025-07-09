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
#

"""Utility functions.

Warning: This is an internal part of the library and might change without notice.
"""

import json
import os
from collections.abc import Mapping, Set
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from typing import Any

import jsonschema
import jsonschema.exceptions
import jsonschema.protocols
import jsonschema.validators
import ruamel.yaml
from arcticfreeze import FrozenDict
from pydantic import BaseModel

from schemapack.exceptions import ParsingError

yaml = ruamel.yaml.YAML(typ="rt")
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.default_flow_style = False


def read_json_or_yaml_mapping(path: Path) -> dict:
    """Reads a JSON object or YAML mapping from file.

    Raises:
        ParsingError:
            If the file cannot be decoded as JSON or YAML or does not contain a
            JSON object or YAML Mapping. Please note, that this parser raise a
            ParsingError for duplicate keys in both JSON objects and YAML mappings.
    """
    with path.open("r", encoding="utf-8") as file:
        try:
            data = yaml.load(file)
        except ruamel.yaml.YAMLError as error:
            raise ParsingError(
                f"The file at '{path}' could not be parsed as JSON or YAML."
            ) from error

    if not isinstance(data, dict):
        raise ParsingError(
            f"The file at '{path}' did not contain a JSON object or a YAML mapping."
        )

    return data


class JsonSchemaError(ValueError):
    """Raised when a JSON schema is invalid."""


def assert_valid_json_schema(schema: Mapping[str, Any]) -> None:
    """Asserts that the given mapping is a valid JSON Schema.

    Raises:
        JsonSchemaError: If the schema is invalid.
    """
    cls: type[jsonschema.protocols.Validator] = jsonschema.validators.validator_for(
        schema
    )
    if isinstance(schema, FrozenDict):
        schema = thaw(schema)
    try:
        cls.check_schema(schema)
    except jsonschema.exceptions.SchemaError as error:
        raise JsonSchemaError(error.message) from error


@contextmanager
def transient_directory_change(path: Path):
    """Change the current working directory temporarily within a with block."""
    original_cwd = os.getcwd()
    os.chdir(path)

    try:
        yield
    finally:
        os.chdir(original_cwd)


def model_to_serializable_dict(
    model: BaseModel,
) -> dict[str, Any]:
    """Converts the provided pydantic model to a JSON-serializable dictionary.

    Returns:
        A dictionary representation of the provided model.
    """
    return json.loads(model.model_dump_json(exclude_defaults=True))


def thaw(frozen: Any) -> Any:
    """Recursively thaws potentially frozen data structures into mutable ones, replacing
    any mappings with dictionaries and tuples with lists.
    """
    if isinstance(frozen, Mapping):
        return {key: thaw(value) for key, value in frozen.items()}
    elif isinstance(frozen, Set):
        return {thaw(item) for item in frozen}
    elif isinstance(frozen, list | tuple):
        return [thaw(item) for item in frozen]
    else:
        return frozen


def dumps_model(
    model: BaseModel,
    *,
    yaml_format: bool = True,
) -> str:
    """Dumps the provided pydantic model as a JSON or YAML-formatted string.

    Args:
        model:
            The model to dump.
        yaml_format:
            Whether to dump as YAML (`True`) or JSON (`False`).
    """
    model_dict = model_to_serializable_dict(model)

    if yaml_format:
        with StringIO() as buffer:
            yaml.dump(model_dict, buffer)
            return buffer.getvalue().strip()

    return json.dumps(model_dict, indent=2)


def write_dict(dict_: dict, *, path: Path, yaml_format: bool) -> None:
    """Writes the provided dictionary to a file at the provided path."""
    if yaml_format:
        with open(path, "w", encoding="utf-8") as file:
            yaml.dump(dict_, file)
    else:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(dict_, file, indent=2)
