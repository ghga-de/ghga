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

"""Batch processing for the upload process"""

import asyncio
import logging
import signal
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import SecretBytes

from ghga_connector import exceptions
from ghga_connector.constants import BATCH_RETRY_BACKOFF_SEC, DEFAULT_BATCH_MAX_RETRIES
from ghga_connector.core import CLIMessageDisplay, utils
from ghga_connector.core.crypt.encryption import Crypt4GHEncryptor
from ghga_connector.core.uploading.api_calls import UploadClient
from ghga_connector.core.uploading.structs import CoreFileInfo, FileInfoForUpload
from ghga_connector.core.uploading.uploader import Uploader

log = logging.getLogger(__name__)

# The file state, as reported by the Upload API, that marks a cancelled (deleted)
#  upload. A file in any other state is considered already present in the box.
_CANCELLED_STATE = "cancelled"

# When listing skipped or failed aliases in a message, show at most this many before
#  eliding the rest, so a large resume doesn't print a wall of text.
_MAX_LISTED_ALIASES = 10

# Aliases longer than this are middle-elided (keeping the start and end) when name
#  shortening is enabled, so very long aliases don't blow out the output.
_MAX_NAME_WIDTH = 60

# The marker inserted in place of an elided middle, with surrounding spaces so the
#  break is visually clear.
_ELLIPSIS = " … "

# Only elide when doing so shortens the displayed text by at least this many characters.
#  An elided alias is always _MAX_NAME_WIDTH chars long, so this avoids situations where
#  we'd only save a few chars
_MIN_ELISION_SAVINGS = 10


def _elide_middle(text: str) -> str:
    """Shorten ``text`` to ``max_len`` chars by replacing its middle with an ellipsis.

    The beginning and end are preserved, which keeps the most useful parts of an alias
    visible. Text is only elided when this saves at least ``_MIN_ELISION_SAVINGS``
    characters of width; shorter text is returned unchanged.
    """
    if len(text) < _MAX_NAME_WIDTH + _MIN_ELISION_SAVINGS:
        return text
    keep = _MAX_NAME_WIDTH - len(_ELLIPSIS)  # reserve room for the ellipsis marker
    head = (keep + 1) // 2
    tail = keep - head
    return f"{text[:head]}{_ELLIPSIS}{text[-tail:]}"


def _display_name(name: str, *, shorten: bool) -> str:
    """Return ``name`` middle-elided if ``shorten`` is set, otherwise unchanged."""
    return _elide_middle(name) if shorten else name


def _summarize_aliases(aliases: list[str]) -> str:
    """Render a list of aliases as a comma-separated string, eliding long lists."""
    if len(aliases) <= _MAX_LISTED_ALIASES:
        return ", ".join(aliases)
    shown = ", ".join(aliases[:_MAX_LISTED_ALIASES])
    return f"{shown}, ... (+{len(aliases) - _MAX_LISTED_ALIASES} more)"


def parse_file_info_for_upload(file_info: list[str]) -> list[CoreFileInfo]:
    """Given a list of strings, derive a file alias, path, and size from each item."""
    items: list[CoreFileInfo] = []
    for i, arg in enumerate(file_info, 1):
        if not arg:
            continue
        if "," in arg:
            alias, path = arg.split(",", 1)
            alias = alias.strip()
            if not path.strip():
                raise RuntimeError(
                    f"No path supplied for alias '{alias}' in arg #{i}. Verify input and"
                    + " ensure that alias and file path are separated only by a comma"
                    + " and no whitespace."
                )
            validated_path = utils.parse_file_upload_path(path)
        else:
            validated_path = utils.parse_file_upload_path(arg)
            # Derive the alias from the path as supplied by the user, not from the
            # resolved path, so that a symlink's own name is used rather than the
            # name of its target.
            alias = Path(arg).name
        items.append(
            CoreFileInfo(
                alias=alias,
                path=validated_path,
                decrypted_size=validated_path.stat().st_size,
            )
        )

    # Ensure unique aliases and file paths
    for field_name in ["alias", "path"]:
        utils.detect_duplicates([getattr(x, field_name) for x in items], field_name)

    return items


def load_file_info_from_tsv(tsv_path: Path) -> list[CoreFileInfo]:
    """Load file alias/path pairs from a TSV file.

    The first column must contain the file path and the second column must contain the
    file alias. Blank lines are ignored.

    Raises:
        FileDoesNotExistError: If the TSV itself, or one of the referenced files,
            does not exist.
        RuntimeError: If a non-blank line does not contain both a path and an alias.
        ValueError: If duplicate aliases or file paths are detected.
    """
    if not tsv_path.is_file():
        raise exceptions.FileDoesNotExistError(file_path=tsv_path)

    items: list[CoreFileInfo] = []
    with open(tsv_path, encoding="utf-8") as tsv_file:
        for line_number, raw_line in enumerate(tsv_file, 1):
            line = raw_line.strip()
            if not line:
                continue
            columns = line.split("\t")
            if len(columns) < 2:
                # No tab was found on a non-empty line. The most common cause is a file
                # that uses spaces rather than tabs, so call that out explicitly.
                hint = (
                    " It looks like this line separates the columns with spaces rather"
                    + " than a tab."
                    if " " in line
                    else ""
                )
                raise RuntimeError(
                    f"Line {line_number} of '{tsv_path}' could not be parsed: the file"
                    + " must be tab-separated, with the file path in the first column"
                    + f" and the alias in the second.{hint}"
                )
            path = columns[0].strip()
            alias = columns[1].strip()
            if not path or not alias:
                raise RuntimeError(
                    f"Line {line_number} of '{tsv_path}' is missing a file path or"
                    + " alias. Each non-empty line must have a file path and an alias"
                    + " separated by a tab."
                )
            validated_path = utils.parse_file_upload_path(path)
            items.append(
                CoreFileInfo(
                    alias=alias,
                    path=validated_path,
                    decrypted_size=validated_path.stat().st_size,
                )
            )

    if not items:
        raise RuntimeError(f"No file entries were found in '{tsv_path}'.")

    # Ensure unique aliases and file paths
    for field_name in ["alias", "path"]:
        utils.detect_duplicates([getattr(x, field_name) for x in items], field_name)

    return items


def _signal_handler(signum, frame):
    """Capture KeyboardInterrupt"""
    CLIMessageDisplay.display("Cleanup in progress, please wait…")


async def perform_cleanup(*, uploader: Uploader, alias: str) -> None:
    """Perform file cleanup after an error or user cancellation.

    Prevents subsequent keyboard cancellations from disrupting cleanup process.
    """
    signal.signal(signal.SIGINT, _signal_handler)

    try:
        await uploader.delete_file()
    except BaseException as exc:
        CLIMessageDisplay.failure(str(exc))
        CLIMessageDisplay.failure(
            "Failed to cancel in-progress upload after unhandled exception."
        )
    else:
        CLIMessageDisplay.display(f"File upload for {alias} was cancelled.")
        CLIMessageDisplay.display(
            "Upload process stopped. If applicable, any previously completed"
            + " file uploads remain uploaded."
        )


@dataclass
class BatchPassResult:
    """The outcome of a single pass over a list of files in a batch upload.

    Attributes:
        failed: The files that did not upload successfully during this pass.
        halted: True if the batch was stopped before all files were attempted
            (e.g. the upload box ran out of space or the user aborted). When set,
            the caller should not retry, since retrying cannot help.
    """

    failed: list[FileInfoForUpload] = field(default_factory=list)
    halted: bool = False


async def upload_files_from_list(
    *,
    upload_client: UploadClient,
    file_info_list: list[FileInfoForUpload],
    my_private_key: SecretBytes,
    max_concurrent_uploads: int,
    shorten: bool = False,
) -> BatchPassResult:
    """Upload all files in the provided list of file paths.

    If the user cancels the upload, e.g. via CTRL+C, or if an unexpected error occurs,
    the in progress file will be cancelled and the upload process halted.

    If ``shorten`` is set, long aliases are middle-elided in user-facing messages.

    Returns a ``BatchPassResult`` describing which files failed and whether the pass was
    halted before all files were attempted.
    """
    failed: list[FileInfoForUpload] = []
    for index, file_info in enumerate(file_info_list):
        # Display name for user-facing messages and the progress bar; logs and API
        # calls always use the full alias.
        display_alias = _display_name(file_info.alias, shorten=shorten)
        uploader = Uploader(
            upload_client=upload_client,
            file_info=file_info,
            max_concurrent_uploads=max_concurrent_uploads,
            display_name=display_alias,
        )
        log.info("Initializing upload for %s", file_info.alias)
        log.debug("Full file path is %s", str(file_info.path.resolve()))

        try:
            file_id, storage_alias = await uploader.initiate_file_upload()
        except Exception as err:
            CLIMessageDisplay.failure(str(err))

            # Exit if the error is because the upload box lacks sufficient space
            if isinstance(err.__cause__, exceptions.UploadBoxSizeExceededError):
                CLIMessageDisplay.failure(
                    "Upload process stopped. If applicable, any previously completed"
                    + " file uploads remain uploaded."
                )
                # Retrying is futile, so mark the pass as halted.
                failed.extend(file_info_list[index:])
                return BatchPassResult(failed=failed, halted=True)

            # For other errors, go to next file because there's nothing else to do here
            failed.append(file_info)
            continue
        log.info(
            "File upload successfully initialized for %s."
            + " The generated file ID is %s and the assigned storage alias is %s.",
            file_info.alias,
            file_id,
            storage_alias,
        )

        log.info("Encrypting and uploading %s", file_info.alias)
        encryptor = Crypt4GHEncryptor(
            part_size=file_info.part_size,  # this will be the adjusted part size
            my_private_key=my_private_key,
            file_size=file_info.decrypted_size,
            storage_alias=storage_alias,
        )
        try:
            await uploader.upload_file(encryptor=encryptor)
        except KeyboardInterrupt:
            # User cancellation is handled here
            CLIMessageDisplay.failure(
                f"User aborted upload for {display_alias}, (file ID {file_id}), deleting."
            )
            await perform_cleanup(uploader=uploader, alias=display_alias)
            # An explicit user abort stops the whole batch rather than retrying.
            failed.append(file_info)
            failed.extend(file_info_list[index + 1 :])
            return BatchPassResult(failed=failed, halted=True)
        except BaseException as err:
            # All other errors are handled here
            CLIMessageDisplay.failure(str(err))
            CLIMessageDisplay.failure(
                f"Failed to upload {display_alias}, (file ID {file_id}), deleting."
            )
            await perform_cleanup(uploader=uploader, alias=display_alias)
            failed.append(file_info)
        else:
            # This is the success case
            CLIMessageDisplay.success(f"Successfully uploaded {display_alias}.")

    return BatchPassResult(failed=failed, halted=False)


async def _already_uploaded_aliases(upload_client: UploadClient) -> set[str]:
    """Return the set of aliases already present (non-cancelled) in the upload box.

    These are queried from the Upload API and are used to skip files that have
    already been uploaded, e.g. by a previous invocation of the batch upload.
    """
    uploads = await upload_client.get_box_uploads()
    return {
        upload.alias
        for upload in uploads
        if (upload.state or "").lower() != _CANCELLED_STATE
    }


def _report_dry_run(pending: list[FileInfoForUpload], *, shorten: bool) -> None:
    """Print the files that would be uploaded, without uploading anything.

    The alias, path and size columns are padded to the widest value in each column
    so they line up vertically for readability. If ``shorten`` is set, long aliases
    are middle-elided.
    """
    total_size = sum(fi.decrypted_size for fi in pending)
    CLIMessageDisplay.display(
        f"Dry run: {len(pending)} file(s) would be uploaded"
        + f" ({utils.human_readable_size(total_size)}). No data will be sent."
    )

    rows = [
        (
            _display_name(fi.alias, shorten=shorten),
            str(fi.path),
            utils.human_readable_size(fi.decrypted_size),
        )
        for fi in pending
    ]
    # Column widths account for both the values and the header labels.
    alias_width = max(len("ALIAS"), *(len(alias) for alias, _, _ in rows))
    path_width = max(len("PATH"), *(len(path) for _, path, _ in rows))
    size_width = max(len("SIZE"), *(len(size) for _, _, size in rows))

    # Header row. The blank runs match the widths of the bullet ("  - "), arrow
    # ("  ->  ") and "  (" decorations in the data rows below, so the labels line up
    # over their columns.
    CLIMessageDisplay.display(
        f"    {'ALIAS':<{alias_width}}      {'PATH':<{path_width}}"
        + f"   {'SIZE':>{size_width}}"
    )
    for alias, path, size in rows:
        CLIMessageDisplay.display(
            f"  - {alias:<{alias_width}}  ->  {path:<{path_width}}"
            + f"  ({size:>{size_width}})"
        )


async def run_batch_upload(  # noqa: PLR0913
    *,
    upload_client: UploadClient,
    file_info_list: list[FileInfoForUpload],
    my_private_key: SecretBytes,
    max_concurrent_uploads: int,
    max_retries: int = DEFAULT_BATCH_MAX_RETRIES,
    dry_run: bool = False,
    shorten: bool = False,
) -> None:
    """Upload a batch of files, skipping those already uploaded and retrying failures.

    Files whose alias is already present in the upload box (in any non-cancelled
    state) are skipped, so re-running the command resumes where a previous run left
    off. Files that fail to upload are retried up to ``max_retries`` times, waiting
    ``BATCH_RETRY_BACKOFF_SEC`` seconds between passes.

    If ``dry_run`` is True, the upload box is still queried so that already-uploaded
    files are reported as skipped, but the files that remain are only listed - no
    uploads are initiated.

    If ``shorten`` is set, long aliases are middle-elided in the output.
    """
    already_uploaded = await _already_uploaded_aliases(upload_client)
    skipped = [fi.alias for fi in file_info_list if fi.alias in already_uploaded]
    if skipped:
        CLIMessageDisplay.display(
            f"Skipping {len(skipped)} file(s) already present in the upload box: "
            + _summarize_aliases([_display_name(a, shorten=shorten) for a in skipped])
        )

    pending = [fi for fi in file_info_list if fi.alias not in already_uploaded]
    if not pending:
        CLIMessageDisplay.success("All files are already uploaded. Nothing to do.")
        return

    if dry_run:
        _report_dry_run(pending, shorten=shorten)
        return

    CLIMessageDisplay.display(f"Uploading {len(pending)} file(s)...")
    attempt = 0
    halted = False
    while True:
        result = await upload_files_from_list(
            upload_client=upload_client,
            file_info_list=pending,
            my_private_key=my_private_key,
            max_concurrent_uploads=max_concurrent_uploads,
            shorten=shorten,
        )
        pending = result.failed

        if not pending:
            CLIMessageDisplay.success(
                "Batch upload complete. All files uploaded successfully."
            )
            return

        # A halted pass (box full or user abort) is not retried.
        # Note: If `halted=True`, the cause is already logged via CLIMessageDisplay
        if result.halted or attempt >= max_retries:
            halted = result.halted

            if attempt >= max_retries:
                CLIMessageDisplay.failure("All retries exhausted.")
            break

        attempt += 1
        CLIMessageDisplay.display(
            f"Retrying {len(pending)} failed file(s) in {BATCH_RETRY_BACKOFF_SEC}s"
            + f" (retry {attempt}/{max_retries})..."
        )
        await asyncio.sleep(BATCH_RETRY_BACKOFF_SEC)

    aliases = _summarize_aliases(
        [_display_name(fi.alias, shorten=shorten) for fi in pending]
    )
    if halted:
        # The stop reason was already reported by upload_files_from_list.
        CLIMessageDisplay.failure(
            f"{len(pending)} file(s) were not uploaded: {aliases}"
        )
    else:
        retry_word = "retry" if max_retries == 1 else "retries"
        CLIMessageDisplay.failure(
            f"{len(pending)} file(s) did not upload after {max_retries} {retry_word}:"
            + f" {aliases}"
        )
