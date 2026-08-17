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

"""Various helper functions"""

import logging
import os
import sys
import warnings
from collections.abc import Callable
from contextlib import redirect_stderr
from functools import partial
from getpass import GetPassWarning, getpass
from io import StringIO
from pathlib import Path
from types import TracebackType
from typing import Any

import crypt4gh.keys
from pydantic import SecretBytes

from ghga_connector import exceptions
from ghga_connector.constants import PASSPHRASE_ENV_VAR
from ghga_connector.core.downloading.structs import FileInfo
from ghga_connector.core.message_display import CLIMessageDisplay

log = logging.getLogger(__name__)


class _KeyIsEncrypted(BaseException):
    """Raised from the passphrase callback to report that a key is encrypted.

    It derives from `BaseException` so that it escapes crypt4gh, which turns every
    `Exception` raised while parsing a key into a process exit.
    """


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


def prompt_for_passphrase() -> str | None:
    """Ask the user for the private key passphrase without echoing it.

    Returns None if there is no terminal to ask on, so that a script is not held up
    waiting for an answer that cannot be given.
    """
    if sys.stdin is None or not sys.stdin.isatty():
        return None
    try:
        with warnings.catch_warnings():
            # `getpass` warns instead of failing when it cannot turn the terminal's
            #  echo off, and then reads the passphrase in plain, visible text. The
            #  warning is raised before it reads anything, so turning it into an error
            #  keeps the passphrase off the screen (and out of any terminal log).
            warnings.simplefilter("error", GetPassWarning)
            passphrase = getpass("Passphrase for your private key: ")
    except (EOFError, GetPassWarning):
        return None
    return passphrase or None


def get_passphrase() -> str | None:
    """Get the passphrase for an encrypted private key.

    It is taken from the environment if that variable is set, which keeps unattended
    runs possible, and asked for interactively otherwise. It is deliberately not
    accepted as a command line option, as that would leave it in the shell history
    and expose it to everyone who can list the running processes.
    """
    return os.environ.get(PASSPHRASE_ENV_VAR) or prompt_for_passphrase()


def _signal_encrypted_key() -> str:
    """Report back that the key being read is encrypted, instead of unlocking it"""
    raise _KeyIsEncrypted()


def _read_private_key(
    my_private_key_path: Path, callback: Callable[[], str]
) -> SecretBytes:
    """Read the private key, keeping crypt4gh's own error output off the screen.

    crypt4gh prints its own "Invalid Key or Passphrase" line before exiting. It is
    swallowed here because the errors raised by the caller say the same thing more
    precisely. It remains visible as a log record in debug mode.
    """
    with redirect_stderr(StringIO()):
        return SecretBytes(
            crypt4gh.keys.get_private_key(
                filepath=my_private_key_path, callback=callback
            )
        )


def get_private_key(my_private_key_path: Path) -> SecretBytes:
    """Get the user's private key, asking for a passphrase only if it is encrypted"""
    if not my_private_key_path.is_file():
        raise exceptions.PrivateKeyFileDoesNotExistError(
            private_key_path=my_private_key_path
        )

    try:
        # crypt4gh only calls the callback once it knows that the key is encrypted,
        #  so unencrypted keys are read without bothering the user at all
        return _read_private_key(my_private_key_path, _signal_encrypted_key)
    except _KeyIsEncrypted:
        pass
    except ValueError as error:
        # raised by crypt4gh before it starts parsing, e.g. for a non-PEM file
        raise exceptions.PrivateKeyFileInvalidError(
            private_key_path=my_private_key_path, reason=str(error)
        ) from error
    except SystemExit as error:
        # crypt4gh exits the process for any error while parsing the key
        raise exceptions.PrivateKeyFileInvalidError(
            private_key_path=my_private_key_path,
            reason="it could not be parsed as a Crypt4GH or OpenSSH private key",
        ) from error

    # the passphrase is asked for out here, where crypt4gh's output is not redirected,
    #  so that the prompt cannot get swallowed along with it
    passphrase = get_passphrase()
    if not passphrase:
        raise exceptions.PassphraseRequiredError(private_key_path=my_private_key_path)

    try:
        return _read_private_key(my_private_key_path, lambda: passphrase)
    except SystemExit as error:
        raise exceptions.InvalidPassphraseError(
            private_key_path=my_private_key_path
        ) from error


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


def parse_file_upload_path(s: str) -> Path:
    """Ensure the specified path points to an existing file for upload"""
    path = Path(s).resolve()
    if not (path.exists() and path.is_file()):
        raise exceptions.FileDoesNotExistError(file_path=path)
    return path


def detect_duplicates(values: list[Any], field_name: str = ""):
    """Raise an error if there are duplicate values in the list"""
    if len(set(values)) < len(values):
        raise ValueError(f"Duplicate {field_name} values detected.")


def human_readable_size(num_bytes: int | None) -> str:
    """Render a byte count in a compact, human-readable form."""
    if num_bytes is None:
        return "-"
    size = float(num_bytes)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB"):
        if abs(size) < 1024 or unit == "PiB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PiB"
