# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
# for the German Human Genome-Phenome Archive (GHGA)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utilities used in fixtures"""

import hashlib
import os
import tempfile
from contextlib import contextmanager

import yaml


@contextmanager
def temporary_file(file_path, content):
    """Yield the temporary file with required content."""
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)
        yield file_path
    finally:
        os.remove(file_path)


def write_data_to_yaml(data: dict[str, str], file_path=None):
    """Serialize the given dictionary to a YAML file."""
    if not file_path:
        _, file_path = tempfile.mkstemp()  # pylint: disable=consider-using-with

    with open(file_path, "w", encoding="utf-8") as file_:
        yaml.dump(data, file_)

    return file_path


def calculate_checksum(file_contents: bytes) -> str:
    """Compute the SHA256 hash of a file."""
    return hashlib.sha256(file_contents).hexdigest()
