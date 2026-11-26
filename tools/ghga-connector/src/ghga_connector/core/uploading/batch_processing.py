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
import contextlib
import enum
import logging
import math
import signal
from collections.abc import Collection, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import SecretBytes

from ghga_connector import exceptions
from ghga_connector.constants import BATCH_RETRY_BACKOFF_SEC, DEFAULT_BATCH_MAX_RETRIES
from ghga_connector.core import CLIMessageDisplay, utils
from ghga_connector.core.crypt.encryption import Crypt4GHEncryptor
from ghga_connector.core.file_operations import is_file_encrypted
from ghga_connector.core.progress_bar import BatchUploadProgress
from ghga_connector.core.uploading.api_calls import UploadClient
from ghga_connector.core.uploading.structs import CoreFileInfo, FileInfoForUpload
from ghga_connector.core.uploading.uploader import FairSlots, Uploader

log = logging.getLogger(__name__)

USER_ABORT_EXCEPTIONS = (KeyboardInterrupt, asyncio.CancelledError)

# The file states, as reported by the Upload API, that mark a cancelled (deleted) or
#  failed upload, whose file can be uploaded again, and an upload that was started
#  but not completed. A file in any other state is considered already uploaded.
_CANCELLED_STATE = "cancelled"
_FAILED_STATE = "failed"
_UNFINISHED_STATE = "init"

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


class _SigintDeferred:
    """Swallow Ctrl+C while any cleanup runs, and restore the handler after the last.

    Cleanups of several files in flight overlap. If each swapped the handler on its
    own, they would restore each other's, and the last could leave this one in place.
    """

    def __init__(self) -> None:
        self._running = 0
        self._previous: Any = None

    @contextmanager
    def __call__(self) -> Iterator[None]:
        """Keep Ctrl+C from interrupting the cleanup inside this context."""
        if not self._running:
            self._previous = signal.signal(signal.SIGINT, _signal_handler)
        self._running += 1
        try:
            yield
        finally:
            self._running -= 1
            if not self._running:
                signal.signal(signal.SIGINT, self._previous)


_defer_sigint = _SigintDeferred()


async def perform_cleanup(*, uploader: Uploader, alias: str) -> None:
    """Perform file cleanup after an error or user cancellation.

    Prevents a keyboard cancellation from disrupting the cleanup itself by swallowing
    SIGINT for the duration of the cleanup, then restoring the previous handler so that
    subsequent files in the batch can still be aborted with Ctrl+C.

    Note: ``signal.signal()`` only works on the main thread, which is where the CLI runs
    (via ``asyncio.run``), so this is safe here.
    """
    with _defer_sigint():
        deletion = asyncio.ensure_future(uploader.delete_file())
        stopped = False
        # A cancellation meanwhile (another file's abort, SIGTERM or SIGHUP after
        #  Ctrl+C) must not cut the deletion off and leave the upload in the box
        while not deletion.done():
            try:
                await asyncio.wait({deletion})
            except asyncio.CancelledError:
                stopped = True
        exc = None if deletion.cancelled() else deletion.exception()
        if exc is not None:
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
    if stopped:
        # The batch was stopped during the cleanup: pass that on
        raise asyncio.CancelledError


@dataclass
class BatchPassResult:
    """The outcome of a single pass over a list of files in a batch upload.

    Attributes:
        failed: The files that did not upload successfully during this pass.
        rejected: The files that were rejected because they are already Crypt4GH
            encrypted. Unlike `failed`, these must not be retried, since the file
            content will not change between passes.
        halted: True if the batch was stopped before all files were attempted
            (e.g. the upload box ran out of space or the user aborted). When set,
            the caller should not retry, since retrying cannot help.
    """

    failed: list[FileInfoForUpload] = field(default_factory=list)
    rejected: list[FileInfoForUpload] = field(default_factory=list)
    halted: bool = False


class _Outcome(enum.Enum):
    """How the upload of one file in a pass ended."""

    UPLOADED = enum.auto()
    FAILED = enum.auto()
    REJECTED = enum.auto()
    # The box has no room for the file: start no further file
    BOX_FULL = enum.auto()
    # The box holds the most open uploads it accepts: try again once one ends
    AT_UPLOAD_LIMIT = enum.auto()
    # The user stopped the batch: stop every file in flight
    ABORTED = enum.auto()


@dataclass
class _FileUploadContext:
    """What the uploads of one pass share."""

    upload_client: UploadClient
    my_private_key: SecretBytes
    budget: asyncio.Semaphore
    parts: int
    per_file: int
    progress: BatchUploadProgress
    shorten: bool
    overwrite: bool
    # Run from the ubox shell, whose user frees the box with `rm`
    in_shell: bool = False
    # The aliases of the files whose upload UCS created and that have not ended yet
    created: set[str] = field(default_factory=set)


async def _upload_one_file(  # noqa: C901, PLR0911
    file_info: FileInfoForUpload, context: _FileUploadContext, part_slots: FairSlots
) -> _Outcome:
    """Upload one file of a batch and report how it ended.

    A file that fails, or that the user aborts during its upload, is deleted from the
    box again.
    """
    # Display name for user-facing messages and the progress bar; logs and API
    # calls always use the full alias.
    display_alias = _display_name(file_info.alias, shorten=context.shorten)

    log.info("Checking whether %s is already Crypt4GH encrypted.", file_info.alias)
    try:
        already_encrypted = is_file_encrypted(file_info.path)
    except OSError as err:
        CLIMessageDisplay.failure(f"Could not read the file for {display_alias}: {err}")
        return _Outcome.FAILED
    if already_encrypted:
        CLIMessageDisplay.failure(
            str(exceptions.FileAlreadyEncryptedError(file_path=file_info.path))
        )
        return _Outcome.REJECTED

    uploader = Uploader(
        upload_client=context.upload_client,
        file_info=file_info,
        part_slots=part_slots,
        display_name=display_alias,
        overwrite=context.overwrite,
        progress=context.progress,
    )
    log.info("Initializing upload for %s", file_info.alias)
    log.debug("Full file path is %s", str(file_info.path.resolve()))

    try:
        file_id, storage_alias = await uploader.initiate_file_upload()
    except USER_ABORT_EXCEPTIONS:
        if uploader.created:
            # UCS created the upload before the abort: delete it again
            with contextlib.suppress(asyncio.CancelledError):
                await perform_cleanup(uploader=uploader, alias=display_alias)
            return _Outcome.ABORTED
        CLIMessageDisplay.failure(
            f"Cancelled upload for {display_alias}. It is possible that the server-"
            + "side upload was created anyway. If you are unable to create a new"
            + f" upload for {display_alias} because of this, remove the server-side"
            + f" upload by running `ghga-connector ubox`, then `rm {display_alias}`."
        )
        return _Outcome.ABORTED
    except Exception as err:
        # Wait if the box has no room for another open upload; the caller decides
        if isinstance(err.__cause__, exceptions.TooManyOpenUploadsError):
            return _Outcome.AT_UPLOAD_LIMIT

        CLIMessageDisplay.failure(str(err))

        # Stop if the error is because the upload box lacks sufficient space
        if isinstance(err.__cause__, exceptions.UploadBoxSizeExceededError):
            CLIMessageDisplay.failure(
                "Upload process stopped. If applicable, any previously completed"
                + " file uploads remain uploaded."
            )
            return _Outcome.BOX_FULL

        # For other errors, go to next file because there's nothing else to do here
        return _Outcome.FAILED
    context.created.add(file_info.alias)
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
        my_private_key=context.my_private_key,
        file_size=file_info.decrypted_size,
        storage_alias=storage_alias,
    )
    try:
        await uploader.upload_file(encryptor=encryptor)
    except USER_ABORT_EXCEPTIONS:
        # User cancellation is handled here.
        CLIMessageDisplay.failure(
            f"Upload aborted for {display_alias}, (file ID {file_id}), deleting."
        )
        with contextlib.suppress(asyncio.CancelledError):
            await perform_cleanup(uploader=uploader, alias=display_alias)
        return _Outcome.ABORTED
    except BaseException as err:
        # All other errors are handled here
        CLIMessageDisplay.failure(str(err))
        CLIMessageDisplay.failure(
            f"Failed to upload {display_alias}, (file ID {file_id}), deleting."
        )
        try:
            await perform_cleanup(uploader=uploader, alias=display_alias)
        except asyncio.CancelledError:
            # Stopped during the cleanup: start no further file
            return _Outcome.ABORTED
        return _Outcome.FAILED

    CLIMessageDisplay.success(f"Successfully uploaded {display_alias}.")
    return _Outcome.UPLOADED


async def upload_files_from_list(  # noqa: PLR0913
    *,
    upload_client: UploadClient,
    file_info_list: list[FileInfoForUpload],
    my_private_key: SecretBytes,
    max_concurrent_uploads: int,
    max_concurrent_files: int = 1,
    shorten: bool = False,
    overwrite: bool = False,
    restart: Collection[str] = (),
    in_shell: bool = False,
) -> BatchPassResult:
    """Upload all files in the provided list of file paths.

    Up to ``max_concurrent_files`` files upload at the same time, largest first. They
    share ``max_concurrent_uploads`` parts in flight, each file at most its equal
    share of them. Files whose alias is in ``restart`` go first: with ``overwrite``
    they replace their unfinished upload, so the box's limit of open uploads cannot
    refuse them.

    If the user cancels the upload, e.g. via CTRL+C, every file in flight is deleted
    and the upload process halted. If the upload box has no room for a file, no
    further file starts, the files in flight finish, and the process halts. A file
    that fails otherwise is deleted, and the other files go on.

    If ``shorten`` is set, long aliases are middle-elided in user-facing messages.
    If ``in_shell`` is set, the messages advise the commands of the ubox shell.

    If ``overwrite`` is set, every file is initiated with overwrite=True, so the Upload
    API replaces any existing FileUpload for a given alias instead of rejecting the request.

    Each file is inspected for pre-existing Crypt4GH encryption right before its
    upload starts. Files that are already encrypted are rejected and reported via the
    result's ``rejected`` list; they are never retried.

    Returns a ``BatchPassResult`` describing which files failed, in input order, and
    whether the pass was halted before all files were attempted.
    """
    with BatchUploadProgress() as progress:
        batch_pass = _BatchPass(
            file_info_list,
            _FileUploadContext(
                upload_client=upload_client,
                my_private_key=my_private_key,
                budget=asyncio.Semaphore(max_concurrent_uploads),
                parts=max_concurrent_uploads,
                per_file=math.ceil(
                    max_concurrent_uploads
                    / max(1, min(max_concurrent_files, len(file_info_list)))
                ),
                progress=progress,
                shorten=shorten,
                overwrite=overwrite,
                in_shell=in_shell,
            ),
            restart=restart,
        )
        await batch_pass.run(max_concurrent_files)
    return batch_pass.result()


class _BatchPass:
    """One pass over the files of a batch, with several workers taking files in turn."""

    def __init__(
        self,
        file_info_list: list[FileInfoForUpload],
        context: _FileUploadContext,
        restart: Collection[str] = (),
    ):
        self._file_info_list = file_info_list
        self._context = context
        # Restarted files first, then largest first, so the largest file does not end
        #  the pass alone; the sort keeps the input order among files of equal size
        self._queue = sorted(
            enumerate(file_info_list),
            key=lambda item: (item[1].alias in restart, item[1].decrypted_size),
            reverse=True,
        )
        self._outcomes: dict[int, _Outcome] = {}
        self._workers: list[asyncio.Task] = []
        # The part slots of the files in flight
        self._in_flight: set[FairSlots] = set()
        self._stopped = False
        # Workers uploading a file; those that wait for room in the box are not
        self._busy = 0
        self._file_ended = asyncio.Condition()
        # Files whose wait for room the user was told about, so it is said once
        self._announced: set[str] = set()

    async def run(self, max_concurrent_files: int) -> None:
        """Upload the files with up to `max_concurrent_files` workers."""
        for _ in range(min(max_concurrent_files, len(self._file_info_list))):
            self._workers.append(asyncio.create_task(self._work()))
        try:
            await asyncio.gather(*self._workers)
        except asyncio.CancelledError:
            # The user stopped the batch. The gather waited for the workers, which
            #  deleted their files in flight.
            self._stopped = True
        except BaseException:
            # An unexpected error: the other workers delete their files in flight
            for worker in self._workers:
                worker.cancel()
            await asyncio.gather(*self._workers, return_exceptions=True)
            raise

    async def _work(self) -> None:
        """Upload files from the queue until it is empty or the pass stops."""
        while self._queue and not self._stopped:
            index, file_info = self._queue.pop(0)
            self._busy += 1
            slots = FairSlots(self._context.budget, self._context.per_file)
            self._in_flight.add(slots)
            try:
                outcome = await _upload_one_file(file_info, self._context, slots)
            finally:
                self._busy -= 1
                self._in_flight.discard(slots)
                self._context.created.discard(file_info.alias)
            if outcome is _Outcome.AT_UPLOAD_LIMIT:
                # The file goes back to the head of the queue, for after the wait
                self._queue.insert(0, (index, file_info))
                await self._wait_for_room(file_info)
                continue
            self._outcomes[index] = outcome
            async with self._file_ended:
                self._file_ended.notify()
            if outcome in (_Outcome.BOX_FULL, _Outcome.ABORTED):
                self._stopped = True
            if outcome is _Outcome.ABORTED:
                # Stop the other files in flight too, as asyncio does on Ctrl+C
                for worker in self._workers:
                    if worker is not asyncio.current_task():
                        worker.cancel()
        # With fewer files left in flight, each may take a larger share of the parts
        share = math.ceil(self._context.parts / max(1, len(self._in_flight)))
        for slots in self._in_flight:
            slots.widen(share)
        # A worker that leaves ends no further file, so it wakes every file waiting
        #  for room: they find the queue empty or the pass stopped, or start a file
        async with self._file_ended:
            self._file_ended.notify_all()

    async def _wait_for_room(self, file_info: FileInfoForUpload) -> None:
        """Wait until one of this pass's files ends and frees an open upload.

        With none of them in flight, only uploads that are not this pass's fill the
        box, and nothing here can free them: the pass stops and names them.
        """
        async with self._file_ended:
            if not self._busy:
                self._stopped = True
                self._file_ended.notify_all()
            else:
                # Busy files may still be in their own create and be refused alike:
                #  announce the wait only while one of them holds an open upload
                if file_info.alias not in self._announced and self._context.created:
                    self._announced.add(file_info.alias)
                    display_alias = _display_name(
                        file_info.alias, shorten=self._context.shorten
                    )
                    CLIMessageDisplay.display(
                        "The upload box holds the most open uploads it accepts, so"
                        + f" {display_alias} waits for another file of this batch"
                        + " to end."
                    )
                try:
                    await self._file_ended.wait()
                except asyncio.CancelledError:
                    # The batch was stopped while this file waited
                    self._stopped = True
                return
        await self._report_upload_limit()

    async def _report_upload_limit(self) -> None:
        """Tell the user which open uploads fill the box and how to free it."""
        try:
            _, unfinished = await _aliases_in_box(self._context.upload_client)
        except Exception as err:
            log.warning("Could not list the upload box: %s", err)
            unfinished = set()
        listed = _summarize_aliases(
            [
                _display_name(a, shorten=self._context.shorten)
                for a in sorted(unfinished)
            ]
        )
        CLIMessageDisplay.failure(
            "Upload process stopped: the upload box holds the most open uploads it"
            + " accepts, and none of them belongs to this batch's files in flight."
            + (f" Unfinished uploads in the box: {listed}." if listed else "")
            + " If no other Connector is uploading them,"
            + (
                " remove them with `rm ALIAS`."
                if self._context.in_shell
                else " remove them by running `ghga-connector ubox`, or run the command"
                + " again with --overwrite to restart those that belong to this batch."
            )
        )

    def result(self) -> BatchPassResult:
        """Return the failed and rejected files in input order, and whether the pass
        stopped early. A file that never started counts as failed.
        """
        failed: list[FileInfoForUpload] = []
        rejected: list[FileInfoForUpload] = []
        for index, file_info in enumerate(self._file_info_list):
            outcome = self._outcomes.get(index)
            if outcome is _Outcome.REJECTED:
                rejected.append(file_info)
            elif outcome is not _Outcome.UPLOADED:
                failed.append(file_info)
        return BatchPassResult(failed=failed, rejected=rejected, halted=self._stopped)


async def _aliases_in_box(upload_client: UploadClient) -> tuple[set[str], set[str]]:
    """Return the aliases of the files in the upload box as (uploaded, unfinished).

    Unfinished uploads were started but not completed, e.g. by an interrupted run.
    Cancelled and failed uploads are in neither set.
    """
    uploaded: set[str] = set()
    unfinished: set[str] = set()
    for upload in await upload_client.get_box_uploads():
        state = (upload.state or "").lower()
        if state == _UNFINISHED_STATE:
            unfinished.add(upload.alias)
        elif state not in {_CANCELLED_STATE, _FAILED_STATE}:
            uploaded.add(upload.alias)
    return uploaded, unfinished


def _select_pending(
    file_info_list: list[FileInfoForUpload],
    *,
    uploaded: set[str],
    unfinished: set[str],
    overwrite: bool,
    shorten: bool,
) -> list[FileInfoForUpload]:
    """Return the files to upload, telling the user which ones are left out and why."""
    skipped = [fi.alias for fi in file_info_list if fi.alias in uploaded]
    if skipped:
        CLIMessageDisplay.display(
            f"Skipping {len(skipped)} file(s) already present in the upload box: "
            + _summarize_aliases([_display_name(a, shorten=shorten) for a in skipped])
        )

    interrupted = [fi.alias for fi in file_info_list if fi.alias in unfinished]
    if interrupted:
        _report_unfinished(interrupted, overwrite=overwrite, shorten=shorten)

    left_out = uploaded if overwrite else uploaded | unfinished
    pending = [fi for fi in file_info_list if fi.alias not in left_out]
    if not pending and not interrupted:
        CLIMessageDisplay.success("All files are already uploaded. Nothing to do.")
    return pending


def _report_unfinished(aliases: list[str], *, overwrite: bool, shorten: bool) -> None:
    """Tell the user that these files' uploads are unfinished and what happens to them.

    Another Connector may still be sending such an upload, so it is only restarted
    on request.
    """
    listed = _summarize_aliases([_display_name(a, shorten=shorten) for a in aliases])
    if overwrite:
        CLIMessageDisplay.display(
            f"Restarting {len(aliases)} file(s) whose upload in the box is unfinished:"
            + f" {listed}"
        )
    else:
        CLIMessageDisplay.display(
            f"Skipping {len(aliases)} file(s) whose upload in the box is unfinished,"
            + f" e.g. after an interrupted run: {listed}. If no other Connector is"
            + " uploading them, run the command again with --overwrite to restart"
            + " them."
        )


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


def _report_batch_outcome(  # noqa: PLR0913
    *,
    pending: list[FileInfoForUpload],
    rejected: list[FileInfoForUpload],
    halted: bool,
    max_retries: int,
    shorten: bool,
    left_unfinished: list[FileInfoForUpload] | None = None,
) -> None:
    """Print the final summary of a batch upload run.

    Success is only reported when nothing is left pending and no file was rejected
    for being already Crypt4GH encrypted.
    """
    if rejected:
        rejected_aliases = _summarize_aliases(
            [_display_name(fi.alias, shorten=shorten) for fi in rejected]
        )
        CLIMessageDisplay.failure(
            f"{len(rejected)} file(s) were rejected because they are already Crypt4GH"
            + f" encrypted: {rejected_aliases}"
        )

    if left_unfinished:
        CLIMessageDisplay.failure(
            f"{len(left_unfinished)} file(s) were not uploaded because their upload in"
            + " the box is unfinished: "
            + _summarize_aliases(
                [_display_name(fi.alias, shorten=shorten) for fi in left_unfinished]
            )
        )

    if not pending:
        if not rejected and not left_unfinished:
            CLIMessageDisplay.success(
                "Batch upload complete. All files uploaded successfully."
            )
        return

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


async def run_batch_upload(  # noqa: PLR0913
    *,
    upload_client: UploadClient,
    file_info_list: list[FileInfoForUpload],
    my_private_key: SecretBytes,
    max_concurrent_uploads: int,
    max_concurrent_files: int = 1,
    max_retries: int = DEFAULT_BATCH_MAX_RETRIES,
    dry_run: bool = False,
    shorten: bool = False,
    overwrite: bool = False,
) -> None:
    """Upload a batch of files, skipping those already uploaded and retrying failures.

    Up to ``max_concurrent_files`` files upload at the same time, sharing
    ``max_concurrent_uploads`` parts in flight.

    Files already uploaded to the box are skipped, so re-running the command resumes
    where a previous run left off. Files whose upload in the box is unfinished, e.g.
    after an interrupted run, are skipped as well unless ``overwrite`` is True, which
    restarts them. Files that fail to upload are retried up to ``max_retries`` times,
    waiting ``BATCH_RETRY_BACKOFF_SEC`` seconds between passes. Files that turn out
    to be already Crypt4GH encrypted are rejected when it is their turn to upload and
    are not retried.

    If ``dry_run`` is True, the upload box is still queried so that already-uploaded
    files are reported as skipped, but the files that remain are only listed - no
    uploads are initiated.

    If ``shorten`` is set, long aliases are middle-elided in the output.

    If `overwrite` is True, each uploaded file replaces any existing FileUpload for
    its alias as long as it has not reached the "interrogated" state (re-encrypted).
    """
    try:
        uploaded, unfinished = await _aliases_in_box(upload_client)
    except Exception as err:
        CLIMessageDisplay.failure(f"Batch upload failed: {err!s}")
        return

    pending = _select_pending(
        file_info_list,
        uploaded=uploaded,
        unfinished=unfinished,
        overwrite=overwrite,
        shorten=shorten,
    )
    if not pending:
        return

    if dry_run:
        _report_dry_run(pending, shorten=shorten)
        return

    left_unfinished = (
        [] if overwrite else [fi for fi in file_info_list if fi.alias in unfinished]
    )
    CLIMessageDisplay.display(f"Uploading {len(pending)} file(s)...")
    attempt = 0
    halted = False
    rejected: list[FileInfoForUpload] = []
    while True:
        result = await upload_files_from_list(
            upload_client=upload_client,
            file_info_list=pending,
            my_private_key=my_private_key,
            max_concurrent_uploads=max_concurrent_uploads,
            max_concurrent_files=max_concurrent_files,
            shorten=shorten,
            overwrite=overwrite,
            restart=unfinished if overwrite else (),
        )
        pending = result.failed
        rejected.extend(result.rejected)

        if not pending:
            break

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

    _report_batch_outcome(
        pending=pending,
        rejected=rejected,
        halted=halted,
        max_retries=max_retries,
        shorten=shorten,
        left_unfinished=left_unfinished,
    )
