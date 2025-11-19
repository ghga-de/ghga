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

"""Various helper functions"""

import logging
import math
import sys
from functools import partial
from pathlib import Path
from types import TracebackType
from typing import Any

import crypt4gh.keys
import crypt4gh.lib
from pydantic import SecretBytes

from ghga_connector import exceptions
from ghga_connector.core.downloading.structs import FileInfo
from ghga_connector.core.file_operations import is_file_encrypted
from ghga_connector.core.message_display import CLIMessageDisplay

log = logging.getLogger(__name__)


def strtobool(value: str) -> bool:
    """Inplace replacement for distutils.utils"""
    return value.lower() in ("y", "yes", "on", "1", "true", "t")


def exception_hook(
    type_: BaseException,
    value: BaseException,
    traceback: TracebackType | None,
):
    """When debug mode is NOT enabled, gets called to perform final error handling
    before program exits
    """
    message = (
        "An error occurred. Rerun command"
        + " with --debug at the end to see more information."
    )

    if value.args:
        message += f"\n{value.args[0]}"

    CLIMessageDisplay.failure(message)


def modify_for_debug(debug: bool):
    """Enable debug logging and configure exception printing if debug=True"""
    if debug:
        # enable debug logging
        logging.basicConfig(level=logging.DEBUG)
        sys.excepthook = partial(exception_hook)


def get_work_package_token(max_tries: int) -> list[str]:
    """
    Expect the work package id and access token as a colon separated string
    The user will have to input this manually to avoid it becoming part of the
    command line history.
    """
    CLIMessageDisplay.display("\nFetching work package token...")
    for _ in range(max_tries):
        work_package_string = input(
            "Please paste the complete access token "
            + "that you copied from the GHGA data portal: "
        )
        work_package_parts = work_package_string.split(":")
        if not (
            len(work_package_parts) == 2
            and 20 <= len(work_package_parts[0]) < 40
            and 80 <= len(work_package_parts[1]) < 120
        ):
            CLIMessageDisplay.display(
                "Invalid input. Please enter the access token "
                + "you got from the GHGA data portal unaltered."
            )
            continue
        return work_package_parts
    raise exceptions.InvalidWorkPackageToken(tries=max_tries)


def get_public_key(my_public_key_path: Path) -> bytes:
    """Get the user's private key from the path supplied"""
    if not my_public_key_path.is_file():
        raise exceptions.PubKeyFileDoesNotExistError(public_key_path=my_public_key_path)

    return crypt4gh.keys.get_public_key(filepath=my_public_key_path)


def get_private_key(
    my_private_key_path: Path, passphrase: str | None = None
) -> SecretBytes:
    """Get the user's private key, using the passphrase if supplied/needed."""
    if not my_private_key_path.is_file():
        raise exceptions.PrivateKeyFileDoesNotExistError(
            private_key_path=my_private_key_path
        )
    callback = (lambda: passphrase) if passphrase else None
    my_private_key = SecretBytes(
        crypt4gh.keys.get_private_key(filepath=my_private_key_path, callback=callback)
    )
    return my_private_key


def check_for_existing_file(*, file_info: FileInfo, overwrite: bool):
    """Check if a file with the given name already exists and conditionally overwrite it."""
    # check output file
    output_file = file_info.path_once_complete
    if output_file.exists():
        if overwrite:
            CLIMessageDisplay.display(
                f"A file with name '{output_file}' already exists and will be overwritten."
            )
        else:
            CLIMessageDisplay.failure(
                f"A file with name '{output_file}' already exists. Skipping."
            )
            return

    output_file_ongoing = file_info.path_during_download
    if output_file_ongoing.exists():
        output_file_ongoing.unlink()


def check_adjust_part_size(part_size: int, file_size: int) -> int:
    """
    Convert specified part size from MiB to bytes, check if it needs adjustment and
    adjust accordingly
    """
    lower_bound = 5 * 1024**2
    upper_bound = 5 * 1024**3
    part_size = part_size * 1024**2

    # clamp user input part sizes
    if part_size < lower_bound:
        part_size = lower_bound
    elif part_size > upper_bound:
        part_size = upper_bound

    # fixed list for now, maybe change to something more meaningful
    sizes_mib = [2**x for x in range(3, 13)]
    sizes = [size * 1024**2 for size in sizes_mib]

    # encryption will cause growth of ~ 0.0427%, so assume we might
    # need five more parts for this check
    if file_size / part_size > 9_995:
        for candidate_size in sizes:
            if candidate_size > part_size and file_size / candidate_size <= 9_995:
                part_size = candidate_size
                break
        else:
            raise ValueError(
                "Could not find a valid part size that would allow to upload all file parts"
            )

    if part_size != part_size * 1024**2:
        log.info(
            "Part size was adjusted from %iMiB to %iMiB.\nThe configured part size"
            + " would either have yielded more than the supported 10.000 parts or was"
            + " not within the expected bounds (5MiB <= part_size <= 5GiB).",
            part_size,
            part_size / 1024**2,
        )

    return part_size


def calc_number_of_parts(encrypted_file_size: int, part_size: int) -> int:
    """Calculate the number of file parts from the file and part sizes"""
    return math.ceil(encrypted_file_size / part_size)


def parse_file_upload_path(s: str) -> Path:
    """Ensure the specified path points to an existing file for upload"""
    path = Path(s).resolve()
    if not (path.exists() and path.is_file()):
        raise exceptions.FileDoesNotExistError(file_path=path)
    if is_file_encrypted(path):
        raise exceptions.FileAlreadyEncryptedError(file_path=path)
    return path


def detect_duplicates(values: list[Any], field_name: str = ""):
    """Raise an error if there are duplicate values in the list"""
    if len(set(values)) < len(values):
        raise ValueError(f"Duplicate {field_name} values detected.")
