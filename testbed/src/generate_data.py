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
"""Functionality dealing with data generation upload/download"""

import base64
import hashlib
from abc import ABC
from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from typing import BinaryIO, Generator, cast

import crypt4gh.header
import crypt4gh.keys
import crypt4gh.lib

from src.commons import DATA_DIR, FILE_SIZE


class NamedBinaryIO(ABC, BinaryIO):
    """Return type of NamedTemporaryFile."""

    name: str


@contextmanager
def big_temp_file(size: int) -> Generator[NamedBinaryIO, None, None]:
    """Generates a big file with approximately the specified size in bytes."""
    current_size = 0
    current_number = 0
    next_number = 1
    with NamedTemporaryFile("w+b") as temp_file:
        while current_size <= size:
            byte_addition = f"{current_number}\n".encode("ASCII")
            current_size += len(byte_addition)
            temp_file.write(byte_addition)
            previous_number = current_number
            current_number = next_number
            next_number = previous_number + current_number
        temp_file.flush()
        yield cast(NamedBinaryIO, temp_file)


def generate_file():
    """Generate encrypted test file, return both unencrypted and encrypted data as bytes"""
    with big_temp_file(size=FILE_SIZE) as random_data:
        random_data.seek(0)
        data = random_data.read()
        checksum = hashlib.sha256(data).hexdigest()

        with NamedTemporaryFile() as encrypted_file:
            random_data.seek(0)
            private_key = crypt4gh.keys.get_private_key(
                filepath=DATA_DIR / "key.sec", callback=lambda: None
            )
            pub_key = base64.b64decode("qx5g31H7rdsq7sgkew9ElkLIXvBje4RxDVcAHcJD8XY=")
            encryption_keys = [(0, private_key, pub_key)]
            crypt4gh.lib.encrypt(
                keys=encryption_keys, infile=random_data, outfile=encrypted_file
            )
            encrypted_file.seek(0)
            encrypted_data = encrypted_file.read()

            return data, encrypted_data, checksum
