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
#
"""CLI-specific wrappers around core functions."""

import asyncio
from pathlib import Path

import typer

from ghga_connector import exceptions
from ghga_connector.constants import C4GH, DEFAULT_BATCH_MAX_RETRIES
from ghga_connector.core import CLIMessageDisplay
from ghga_connector.core.main import (
    async_batch_upload,
    async_download,
    async_ubox,
    decrypt_file,
)
from ghga_connector.core.utils import modify_for_debug

cli = typer.Typer(no_args_is_help=True)


@cli.command(name="batch-upload", no_args_is_help=True)
def batch_upload(  # noqa: PLR0913
    tsv: Path = typer.Option(
        ...,
        help=(
            "Path to a TSV file describing the files to upload. The first column must"
            + " contain the file path and the second column the file alias. Relative"
            + " file paths can only be used if this command is run from same directory."
            + " Prefer to use absolute paths."
        ),
    ),
    my_public_key_path: Path = typer.Option(
        "./key.pub",
        help="The path to a public key from the key pair that was announced in the "
        + "metadata. Defaults to key.pub in the current folder.",
    ),
    my_private_key_path: Path = typer.Option(
        "./key.sec",
        help="The path to a private key from the key pair that will be used to encrypt the "
        + "crypt4gh envelope. Defaults to key.sec in the current folder.",
    ),
    passphrase: str | None = typer.Option(
        None,
        help="Passphrase for the encrypted private key. "
        + "Only needs to be provided if the key is actually encrypted.",
    ),
    max_retries: int = typer.Option(
        DEFAULT_BATCH_MAX_RETRIES,
        help="Maximum number of automatic retries for files that fail to upload.",
    ),
    dry_run: bool = typer.Option(
        False,
        help="List the files that would be uploaded (after skipping any already in the"
        + " upload box) without uploading anything.",
    ),
    shorten_names: bool = typer.Option(
        False,
        "--shorten-names",
        help="Shorten very long file aliases in the output, keeping the start and end"
        + " (e.g. 'sample-001 … -run5.bam'). Full aliases are shown by default."
        + " This is only for improving readability and does not affect how"
        + " data is sent to GHGA.",
    ),
    debug: bool = typer.Option(
        False, help="Set this option in order to view traceback for errors."
    ),
):
    """Upload a batch of files described by a TSV file.

    Files already present in the upload box are skipped, so the command can be re-run
    to resume an interrupted batch. Files that fail to upload are retried automatically.
    """
    modify_for_debug(debug)
    asyncio.run(
        async_batch_upload(
            tsv=tsv,
            my_public_key_path=my_public_key_path,
            my_private_key_path=my_private_key_path,
            passphrase=passphrase,
            max_retries=max_retries,
            dry_run=dry_run,
            shorten=shorten_names,
        )
    )


@cli.command()
def ubox(
    my_public_key_path: Path = typer.Option(
        "./key.pub",
        help="The path to a public key from the key pair that was announced in the "
        + "metadata. Defaults to key.pub in the current folder.",
    ),
    my_private_key_path: Path = typer.Option(
        "./key.sec",
        help="The path to a private key from the key pair that will be used to encrypt the "
        + "crypt4gh envelope. Defaults to key.sec in the current folder.",
    ),
    passphrase: str | None = typer.Option(
        None,
        help="Passphrase for the encrypted private key. "
        + "Only needs to be provided if the key is actually encrypted.",
    ),
    debug: bool = typer.Option(
        False, help="Set this option in order to view traceback for errors."
    ),
):
    """Open an interactive shell to manage an upload box (upload, ls, rm)."""
    modify_for_debug(debug)
    asyncio.run(
        async_ubox(
            my_public_key_path=my_public_key_path,
            my_private_key_path=my_private_key_path,
            passphrase=passphrase,
        )
    )


@cli.command(no_args_is_help=True)
def download(  # noqa: PLR0913
    *,
    output_dir: Path = typer.Option(
        ..., help="The directory to put the downloaded files into."
    ),
    my_public_key_path: Path = typer.Option(
        "./key.pub",
        help="The path to a public key from the Crypt4GH key pair "
        + "that was announced when the download token was created. "
        + "Defaults to key.pub in the current folder.",
    ),
    my_private_key_path: Path = typer.Option(
        "./key.sec",
        help="The path to a private key from the Crypt4GH key pair "
        + "that was announced when the download token was created. "
        + "Defaults to key.sec in the current folder.",
    ),
    passphrase: str | None = typer.Option(
        None,
        help="Passphrase for the encrypted private key. "
        + "Only needs to be provided if the key is actually encrypted.",
    ),
    debug: bool = typer.Option(
        False, help="Set this option in order to view traceback for errors."
    ),
    overwrite: bool = typer.Option(
        False,
        help="Set to true to overwrite already existing files in the output directory.",
    ),
):
    """Wrapper for the async download function"""
    modify_for_debug(debug)
    asyncio.run(
        async_download(
            output_dir=output_dir,
            my_public_key_path=my_public_key_path,
            my_private_key_path=my_private_key_path,
            passphrase=passphrase,
            overwrite=overwrite,
        )
    )


@cli.command(no_args_is_help=True)
def decrypt(  # noqa: PLR0912, C901
    *,
    input_dir: Path = typer.Option(
        ...,
        help="Path to the directory containing files that should be decrypted using a "
        + "common decryption key.",
    ),
    output_dir: Path | None = typer.Option(
        None,
        help="Optional path to a directory that the decrypted file should be written to. "
        + "Defaults to input dir.",
    ),
    my_private_key_path: Path = typer.Option(
        "./key.sec",
        help="The path to a private key from the Crypt4GH key pair "
        + "that was announced when the download token was created. "
        + "Defaults to key.sec in the current folder.",
    ),
    passphrase: str | None = typer.Option(
        None,
        help="Passphrase for the encrypted private key. "
        + "Only needs to be provided if the key is actually encrypted.",
    ),
    debug: bool = typer.Option(
        False, help="Set this option in order to view traceback for errors."
    ),
):
    """Command to decrypt a downloaded file"""
    modify_for_debug(debug=debug)

    if not input_dir.is_dir():
        raise exceptions.DirectoryDoesNotExistError(directory=input_dir)

    if not output_dir:
        output_dir = input_dir

    if output_dir.exists() and not output_dir.is_dir():
        raise exceptions.OutputPathIsNotDirectory(directory=output_dir)

    if not output_dir.exists():
        CLIMessageDisplay.display(f"Creating output directory '{output_dir}'")
        output_dir.mkdir(parents=True)

    errors = {}
    skipped_files = []
    file_count = 0
    for input_file in input_dir.iterdir():
        if not input_file.is_file() or input_file.suffix != C4GH:
            skipped_files.append(str(input_file))
            continue

        file_count += 1

        # strip the .c4gh extension for the output file
        output_file = output_dir / input_file.with_suffix("").name

        if output_file.exists():
            errors[str(input_file)] = (
                f"File already exists at '{output_file}', will not overwrite."
            )
            continue

        try:
            CLIMessageDisplay.display(f"Decrypting file with id '{input_file}'...")
            decrypt_file(
                input_file=input_file,
                output_file=output_file,
                decryption_private_key_path=my_private_key_path,
                passphrase=passphrase,
            )
        except ValueError as error:
            errors[str(input_file)] = (
                f"Could not decrypt the provided file with the given key.\nError: {str(error)}"
            )
            continue

        CLIMessageDisplay.success(
            f"Successfully decrypted file '{input_file}' to location '{output_dir}'."
        )
    if file_count == 0:
        CLIMessageDisplay.display(
            f"No files were processed because the directory '{input_dir}' contains no "
            + "applicable files."
        )

    if skipped_files:
        CLIMessageDisplay.display(
            f"The following files were skipped as they are not {C4GH} files:"
        )
        for file in skipped_files:
            CLIMessageDisplay.display(f"- {file}")

    if errors:
        CLIMessageDisplay.failure("The following files could not be decrypted:")
        for input_path, cause in errors.items():
            CLIMessageDisplay.failure(f"- {input_path}:\n\t{cause}")
