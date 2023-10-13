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

"""Data models"""

import re
from typing import Optional

from metldata.builtin_transformations.infer_references.path.path_elements import (
    ReferencePathElement,
    ReferencePathElementType,
)

NAME_PATTERN = r"(?!\d)\w+"
ACTIVE_ARROW_PATTERN = rf"\({NAME_PATTERN}\)>"
PASSIVE_ARROW_PATTERN = rf"<\({NAME_PATTERN}\)"
ARROW_PATTERN = rf"(({ACTIVE_ARROW_PATTERN})|({PASSIVE_ARROW_PATTERN}))"
ELEMENT_PATTERN = rf"{NAME_PATTERN}{ARROW_PATTERN}{NAME_PATTERN}"
PATH_RAW_CHAR_PATTERN = r"^[\w><\(\)]+$"
PATH_PATTERN = (
    rf"^{NAME_PATTERN}{ARROW_PATTERN}({NAME_PATTERN}{ARROW_PATTERN})*{NAME_PATTERN}$"
)


class ValidationError(RuntimeError):
    """Raised when a path string was invalid"""


def clean_path_str(path_str: str) -> str:
    """Cleanup whitespaces, newlines, etc."""
    return "".join(path_str.split())


def validate_path_str_characters(path_str: str) -> None:
    """Validates the characters of the an uncleaned path str. The path_str is assumed to
    be cleaned.

    Raises:
        ValidationError: if invalid.
    """
    if not re.match(PATH_RAW_CHAR_PATTERN, path_str):
        raise ValidationError(
            f"The following path string contains invalid characters: {path_str}"
        )


def validate_path_str_format(path_str: str) -> None:
    """Validates the format of the path str. The path_str is assumed to be cleaned.

    Raises:
        ValidationError: if invalid.
    """
    if not re.match(PATH_PATTERN, path_str):
        raise ValidationError(
            f"The following path string has an invalid format: {path_str}"
        )


def validate_string_element(string_element: str) -> None:
    """Validates the format of a string-based path element. The path_str is assumed to
    be cleaned.

    Raises:
        ValidationError: if invalid.
    """
    if not re.match(rf"^{ELEMENT_PATTERN}$", string_element):
        raise ValidationError(
            "The following string-based path element has an invalid format: "
            + string_element
        )


def extract_first_element(*, path_str: str) -> str:
    """Extract the first element of a path_str. The path_str is assumed to be cleaned.

    Raises:
        ValidationError: if no element can be extracted.
    """
    match = re.match(rf"^({ELEMENT_PATTERN}).*$", path_str)

    if not match:
        raise ValidationError(f"Cannot find element in path string: {path_str}")

    return match.group(1)


def get_target_class(*, path_str: str) -> str:
    """Get the target class of a path str. The path_str is assumed to be cleaned."""
    match = re.match(rf"^.*?({NAME_PATTERN})$", path_str)

    if not match:
        raise ValidationError(f"Cannot find target class of path string: {path_str}")

    return match.group(1)


def split_first_element(*, path_str: str) -> tuple[str, Optional[str]]:
    """Return a tuple of the first element and the remaining path string.
    Thereby, the target class of the first element is set as the source class of the
    remaining path.
    The second element is None if the provided path only contained one element.
    The path_str is assumed to be cleaned.
    """
    first_element = extract_first_element(path_str=path_str)
    first_element_target_class = get_target_class(path_str=first_element)

    if first_element == path_str:
        return first_element, None

    remaining_path = path_str[len(first_element) :]
    remaining_path_extended = first_element_target_class + remaining_path

    return first_element, remaining_path_extended


def get_string_elements(*, path_str: str) -> list[str]:
    """Decomposes a path string into elements in string repesentation. The path_str is
    assumed to be cleaned.
    """
    elements: list[str] = []
    remaining_path = path_str

    # extract one element at a time:
    while remaining_path:
        element, remaining_path = split_first_element(  # type: ignore
            path_str=remaining_path
        )
        elements.append(element)

    return elements


def get_element_type(*, string_element: str) -> ReferencePathElementType:
    """Infers the type of the provided string-based element."""
    validate_string_element(string_element)

    return (
        ReferencePathElementType.ACTIVE
        if ">" in string_element
        else ReferencePathElementType.PASSIVE
    )


def get_element_components(*, string_element: str) -> tuple[str, str, str]:
    """Returns a tuple of the source, the slot, and the target of the string-based path
    element.
    """
    # remove the angle:
    string_element_cleaned = string_element.replace(">", "").replace("<", "")

    # extract the source:
    source, slot_and_target = string_element_cleaned.split("(")

    # extract slot and target:
    slot, target = slot_and_target.split(")")

    return source, slot, target


def string_element_to_object(string_element: str) -> ReferencePathElement:
    """Translates a string-based path element into an object-based representation."""
    validate_string_element(string_element)
    type_ = get_element_type(string_element=string_element)
    source, slot, target = get_element_components(string_element=string_element)

    return ReferencePathElement(type_=type_, source=source, slot=slot, target=target)


def path_str_to_object_elements(path_str: str) -> list[ReferencePathElement]:
    """Translates a path string into a list of object-based elements. The path_str is
    assumed to be cleaned.
    """
    validate_path_str_characters(path_str=path_str)
    validate_path_str_format(path_str=path_str)

    string_elements = get_string_elements(path_str=path_str)
    return [
        string_element_to_object(string_element) for string_element in string_elements
    ]
