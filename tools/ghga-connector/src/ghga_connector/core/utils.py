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
import sys
from functools import partial
from pathlib import Path
from types import TracebackType

import crypt4gh.keys
from ghga_service_commons.utils import crypt

from ghga_connector import exceptions
from ghga_connector.core.downloading.structs import FileInfo
from ghga_connector.core.message_display import CLIMessageDisplay
from ghga_connector.core.structs import WorkPackageInformation


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


def get_work_package_information(my_private_key: bytes):
    """Fetch a work package id and work package token and decrypt the token"""
    # get work package access token and id from user input
    work_package_id, work_package_token = get_work_package_token(max_tries=3)
    decrypted_token = crypt.decrypt(data=work_package_token, key=my_private_key)
    return WorkPackageInformation(
        decrypted_token=decrypted_token, package_id=work_package_id
    )


def get_work_package_token(max_tries: int) -> list[str]:
    """
    Expect the work package id and access token as a colon separated string
    The user will have to input this manually to avoid it becoming part of the
    command line history.
    """
    for _ in range(max_tries):
        work_package_string = input(
            "Please paste the complete download token "
            + "that you copied from the GHGA data portal: "
        )
        work_package_parts = work_package_string.split(":")
        if not (
            len(work_package_parts) == 2
            and 20 <= len(work_package_parts[0]) < 40
            and 80 <= len(work_package_parts[1]) < 120
        ):
            CLIMessageDisplay.display(
                "Invalid input. Please enter the download token "
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


def get_private_key(my_private_key_path: Path, passphrase: str | None = None) -> bytes:
    """Get the user's private key, using the passphrase if supplied/needed."""
    if passphrase:
        my_private_key = crypt4gh.keys.get_private_key(
            filepath=my_private_key_path, callback=lambda: passphrase
        )
    else:
        my_private_key = crypt4gh.keys.get_private_key(
            filepath=my_private_key_path, callback=None
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
