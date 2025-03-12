# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Utils for Fixture handling."""

import json
import re
from pathlib import Path

import ruamel.yaml

yaml = ruamel.yaml.YAML()

BASE_DIR = Path(__file__).parent.resolve()
ROOT_DIR = BASE_DIR.parent.parent


def is_valid_yaml(yaml_string: str):
    """
    Checks if the provided YAML string is valid.

    Args:
        yaml_string: The YAML string to validate.

    Returns:
        bool: True if the YAML is valid, False otherwise.
    """
    try:
        yaml.load(yaml_string)
        return True
    except ruamel.yaml.YAMLError:
        return False


def is_valid_json(json_string: str):
    """
    Checks if the provided JSON string is valid.

    Args:
        json_string: The JSON string to validate.

    Returns:
        bool: True if the JSON is valid, False otherwise.
    """
    try:
        json.loads(json_string)
        return True
    except json.JSONDecodeError:
        return False


def assert_formatted_string(string: str, json_format: bool):
    """
    Asserts that the provided string is formatted in the expected format.

    Args:
        string:
            The string to check.
        json_format:
            True if the string should be in JSON format, False if the string should be
            in YAML format.
    """
    if json_format:
        assert is_valid_json(string)
    else:
        assert is_valid_yaml(string)
        assert not is_valid_json(string)


def loads_json_or_yaml_mapping(string: str):
    """
    Loads a JSON or YAML mapping from a string.

    Args:
        string: The JSON or YAML string to load.

    Returns:
        dict: The loaded mapping.
    """
    return yaml.load(string)


def strip_ansi_escape_sequences(text: str) -> str:
    """Removes ansi escape characters from a string.

    Args:
        text (str): Text to be stripped from ansi characters

    Returns:
        text: Text without ansi characters
    """
    return re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", text)
