# Copyright 2021 - 2025 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#

"""Module containing transformation functions"""

from collections.abc import Callable


def to_string(value: int | str) -> str:
    """Converts a value to string"""
    return str(value)


def split_by_semicolon(value: str) -> list[str]:
    """Splits a string by semicolon"""
    return [elem.strip() for elem in value.split(";")]


def to_list() -> Callable:
    """Returns a function that splits a string by semicolon"""
    return split_by_semicolon


def to_attributes() -> Callable:
    """Returns a function to convert string to attributes"""

    def split_one(value: str) -> dict:
        """Returns a dictionary with key, value as keys, splitted string as values"""
        splitted = (elem.strip() for elem in value.split("="))
        return dict(zip(("key", "value"), splitted))

    def split_mult(value: str) -> list[dict]:
        """Converts string to attributes"""
        return [split_one(elem) for elem in split_by_semicolon(value)]

    return split_mult


def snake_case(cv: str) -> str:
    """Converts format of a string to SNAKE_CASE"""
    return cv.replace(" ", "_").upper()


def to_snake_case() -> Callable:
    """Returns a function that converts a string to SNAKE_CASE"""
    return snake_case


def snake_case_list(value: str) -> list[str]:
    """Combines the functions to split_by_semicolon and convert_to_snake_case"""
    list_to_convert = split_by_semicolon(value)
    return [snake_case(elem) for elem in list_to_convert]


def to_snake_case_list() -> Callable:
    """Returns a function that converts a semicolon separated string into a list of snake-cased strings"""
    return snake_case_list


def to_boolean(value: bool | str) -> bool:
    """Converts common string boolean values to bool.

    Accepts: true/false in any casing (e.g., "true", "False", "TRUE").
    """
    if isinstance(value, bool):
        return value
    normalized = value.strip().casefold()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"Invalid boolean string: {value!r}")
