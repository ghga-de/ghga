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

"""Core logic managing FileUnderInterrogation objects and interpreting
InterrogationReports.
"""

import logging
import random
from contextlib import suppress
from datetime import timedelta
from typing import Any, cast

from pydantic import UUID4, SecretBytes

from fis.config import Config
from fis.constants import (
    CLAIM_CANDIDATE_COUNT,
    LEASE_SECONDS,
    MAX_FILES_PER_REQUEST,
)
from fis.core import models
from fis.ports.inbound.interrogation import InterrogationHandlerPort
from fis.ports.outbound.dao import (
    FileDao,
    InterrogationReportDao,
    UploadBoxPriorityDao,
)
from fis.ports.outbound.event_pub import EventPubTranslatorPort
from fis.ports.outbound.interrogation_queue import InterrogationQueuePort
from fis.ports.outbound.secrets import SecretsClientPort
from ghga_event_schemas import pydantic_ as event_schemas
from hexkit.protocols.dao import (
    MultipleHitsFoundError,
    NoHitsFoundError,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    race_condition_retries,
)
from hexkit.utils import now_utc_ms_prec

STATES = event_schemas.FileUploadState
log = logging.getLogger(__name__)

# DHFS sets these afresh on every submission, so they don't tell reports apart.
_TIMING_FIELDS = {"interrogated_at", "wall_time_seconds", "stage_seconds"}


def _precondition_for(file: models.FileUnderInterrogation) -> dict[str, Any]:
    """Build a precondition that matches only the stored copy `file` was read from.

    A file stored before the lease fields existed lacks `times_claimed`, which reads
    as 0 but doesn't match 0. None matches a missing field.
    """
    precondition = file.model_dump()
    if file.times_claimed == 0:
        precondition["times_claimed"] = {"$in": [0, None]}
    return precondition


class InterrogationHandler(InterrogationHandlerPort):
    """This is the core class that manages `FileUnderInterrogation` and
    `InterrogationReport` objects.
    """

    def __init__(  # noqa: PLR0913
        self,
        *,
        config: Config,
        file_dao: FileDao,
        interrogation_report_dao: InterrogationReportDao,
        upload_box_priority_dao: UploadBoxPriorityDao,
        interrogation_queue: InterrogationQueuePort,
        event_publisher: EventPubTranslatorPort,
        secrets_client: SecretsClientPort,
    ):
        self._config = config
        self._file_dao = file_dao
        self._interrogation_report_dao = interrogation_report_dao
        self._upload_box_priority_dao = upload_box_priority_dao
        self._interrogation_queue = interrogation_queue
        self._publisher = event_publisher
        self._secrets_client = secrets_client

    async def check_if_removable(self, *, object_id: UUID4) -> bool:
        """Return `True` if an object can be removed from the interrogation bucket and
        `False` otherwise.
        """
        try:
            file = await self._file_dao.find_one(filter_={"object_id": object_id})
        except NoHitsFoundError:
            # If not found, log a warning, but indicate the file is removable
            log.warning("Did not find a record of a file with ID %s.", object_id)
            return True
        except MultipleHitsFoundError as err:
            # This should never happen, and if it does then we need eyes on it.
            msg = f"Found multiple files with the same object_id of {object_id}"
            log.critical(msg, extra={"object_id": object_id})
            raise RuntimeError(msg) from err
        else:
            return file.can_remove

    async def handle_interrogation_report(
        self, *, report: models.InterrogationReportWithSecret
    ):
        """Handle an interrogation report and publish the appropriate event.

        If the report relays a success, then deposit the secret with EKSS and publish
        an InterrogationSuccess event. Also updates the file in the database with the
        new object ID, bucket ID, and encrypted_size.

        If the report relays a failure, publish an InterrogationFailure event.

        In both cases, set `interrogated=True` and `state_updated` for the
        `FileUnderInterrogation`. On success, set `state="interrogated"`. On failure,
        set `state="failed_interrogation"` and `can_remove=True`.

        Raises:
        - FileNotFoundError if there's no file with the ID specified in the report.
        - SecretDepositionError if there's a problem depositing the secret with EKSS.
        - InterrogationReportConflict if a submitted report contradicts the database.
        """
        # First make sure we have this file
        file_id = report.file_id
        try:
            file = await self._file_dao.get_by_id(file_id)
        except ResourceNotFoundError as err:
            log.error(
                "Can't process report because no file with ID %s exists.", file_id
            )
            raise self.FileNotFoundError(file_id=file_id) from err

        # Check if there is a matching report already in the database
        if await self._check_if_report_is_duplicate(report=report):
            return

        # If this point is reached, it is a new report - proceed normally

        # See if this is a success report or a failure report
        if report.passed:
            await self._handle_successful_report(report=report, file=file)
        else:
            await self._handle_failure_report(report=report, file=file)

    async def _check_if_report_is_duplicate(
        self, *, report: models.InterrogationReportWithSecret
    ) -> bool:
        """Check whether this report has already been processed.

        Returns `True` if the report is a duplicate and should be ignored,
        `False` if it is new and should be processed normally.

        Raises `InterrogationReportConflict` if a report for this file already
        exists but its content differs from the incoming report.
        """
        file_id = report.file_id
        try:
            stored_report = await self._interrogation_report_dao.get_by_id(file_id)
        except ResourceNotFoundError:
            log.debug(
                "No InterrogationReport yet exists for file %s, proceeding.", file_id
            )
            return False
        else:
            # See if the reports differ - the timing differs on every resend
            report_subset = report.model_dump(exclude=_TIMING_FIELDS | {"secret"})
            stored_subset = stored_report.model_dump(exclude=_TIMING_FIELDS)
            # List different fields
            different_fields = {
                k for k, v in report_subset.items() if stored_subset[k] != v
            }
            if different_fields:
                log.critical(
                    "File %s was already interrogated, but FIS received an unexpected"
                    + " subsequent InterrogationReport that contains different results.",
                    file_id,
                    extra={"file_id": file_id, "differing_fields": different_fields},
                )
                raise self.InterrogationReportConflict(file_id=file_id)

            # We've already seen this report, so don't do anything
            log.info(
                "Received duplicate InterrogationReport for file %s, ignoring.",
                file_id,
            )
            return True

    async def _handle_failure_report(
        self,
        *,
        report: models.InterrogationReportWithSecret,
        file: models.FileUnderInterrogation,
    ) -> None:
        """Handle a failed interrogation report.

        Stores the report in the database, publishes an InterrogationFailure event,
        and updates the FileUnderInterrogation state. If the event publish fails,
        the stored report is rolled back and the exception is re-raised.
        """
        # The model_validator on InterrogationReportWithSecret guarantees `reason`
        # is non-None when passed=False, which is how this handler is reached.
        # cast() is a runtime no-op; it only narrows the type for the checker.
        reason = cast(str, report.reason)

        # Store DB copy of report
        await self._interrogation_report_dao.insert(
            models.InterrogationReport(**report.model_dump(exclude={"secret"}))
        )
        log.debug("Stored InterrogationReport for file %s", file.id)

        # If everything goes well, update the FileUnderInterrogation in the DB
        updated_file = file.model_copy(deep=True)
        updated_file.state = "failed_interrogation"
        updated_file.interrogated = True
        updated_file.state_updated = report.interrogated_at
        updated_file.can_remove = True
        await self._file_dao.update(updated_file)
        log.debug("Updated file %s while processing InterrogationReport", file.id)

        # Publish event last. If it fails to publish, we can fire it manually
        await self._publisher.publish_interrogation_failed(
            file_id=report.file_id,
            storage_alias=report.storage_alias,
            interrogated_at=report.interrogated_at,
            reason=reason,
        )
        log.info("Successfully processed failure report for file %s.", report.file_id)

    async def _handle_successful_report(
        self,
        *,
        report: models.InterrogationReportWithSecret,
        file: models.FileUnderInterrogation,
    ) -> None:
        """Handle a successful interrogation report.

        Stores the report in the database and updates the FileUnderInterrogation state,
        deposits the file encryption secret with EKSS, and publishes an
        InterrogationSuccess event. If some error occurs while updating the database,
        the secret is deleted from EKSS.
        """
        # The model_validator on InterrogationReportWithSecret guarantees these
        # fields are non-None when passed=True, which is how this handler is
        # reached. cast() is a runtime no-op; it only narrows types for the checker.
        secret = cast(SecretBytes, report.secret)
        bucket_id = cast(str, report.bucket_id)
        object_id = cast(UUID4, report.object_id)
        encrypted_size = cast(int, report.encrypted_size)
        encrypted_parts_md5 = cast(list[str], report.encrypted_parts_md5)
        encrypted_parts_sha256 = cast(list[str], report.encrypted_parts_sha256)

        # Deposit the secret with the EKSS
        try:
            secret_id = await self._secrets_client.deposit_secret(secret=secret)
        except Exception as err:
            raise self.SecretDepositionError(
                file_id=file.id, reason="See logs for details."
            ) from err

        try:
            # Store DB copy of report
            await self._interrogation_report_dao.insert(
                models.InterrogationReport(**report.model_dump(exclude={"secret"}))
            )
            log.debug("Stored InterrogationReport for file %s", file.id)

            # If everything goes well, update the FileUnderInterrogation in the DB
            # Update file state, size, and object ID
            updated_file = file.model_copy(deep=True)
            updated_file.state = "interrogated"
            updated_file.state_updated = report.interrogated_at
            updated_file.object_id = object_id
            updated_file.bucket_id = bucket_id
            updated_file.encrypted_size = encrypted_size
            updated_file.interrogated = True
            await self._file_dao.update(updated_file)
            log.debug("Updated file %s while processing InterrogationReport", file.id)
        except Exception:
            # If database operations fail, delete the secret. Interrogation will have to
            #  be performed from scratch. If the service spontaneously dies before deleting
            #  the secret, it's not the end of the world.
            log.error(
                "An error prevented successful processing of InterrogationReport for file %s",
                report.file_id,
            )
            await self._secrets_client.delete_secret(secret_id=secret_id)
            log.info(
                "Successfully cleaned out secret for file %s during error handling.",
                report.file_id,
            )
            raise
        else:
            # Publish event last. If it fails to publish, we can fire it manually
            await self._publisher.publish_interrogation_success(
                file_id=report.file_id,
                secret_id=secret_id,
                storage_alias=report.storage_alias,
                bucket_id=bucket_id,
                object_id=object_id,
                interrogated_at=report.interrogated_at,
                encrypted_parts_md5=encrypted_parts_md5,
                encrypted_parts_sha256=encrypted_parts_sha256,
                encrypted_size=encrypted_size,
            )
            log.info(
                "Successfully processed success report for file %s.", report.file_id
            )

    async def process_file_upload(self, *, file: models.FileUnderInterrogation) -> None:
        """Process a newly received file upload event.

        State-by-state behavior:

        - 'init': ignored; FIS does not track files until they reach 'inbox'.
        - 'inbox': insert into the DB if not already present (idempotent). If there's
          already a copy of this file in the 'failed_interrogation' state, it means a
          Data Steward requeued the file for interrogation. In that case, reset the
          interrogation flags and delete the stored report so DHFS picks the file up
          again.
        - 'cancelled' / 'failed': if the file is known, set can_remove=True and update.
          If not known (i.e., it reached this terminal state before ever hitting 'inbox'),
          log at INFO and ignore since this is a known possibility.
        - 'archived': same update path as cancelled/failed (set can_remove=True). If the
          file is unknown, log a warning and ignore.
        - 'interrogated' / 'awaiting_archival': these transitions are owned by
          handle_interrogation_report(), not by this method. If the file is known and
          the incoming timestamp is newer, no update is performed here. If the file is
          unknown (should not happen in normal operation), log a warning and ignore.
        - 'failed_interrogation': ignored, since FIS already recorded the failure while
          handling the interrogation report.

        For a known file without a `box_id`, any event other than 'init' fills it in
        first, even an outdated one. Files stored before FIS kept the `box_id` lack it
        until UCS republishes its events.

        Raises:
        - FileUpdateError if other writes keep changing the file before its missing
          box ID is filled in.
        """
        if file.state == "init":
            return
        if file.state == "inbox":
            with suppress(ResourceAlreadyExistsError):
                await self._file_dao.insert(file)
                return

        # If we make it past that block, then it is not new and we must compare.
        # A claim between the read and the box ID write would be overwritten, so a
        #  lost race reads the file again, lease included
        async for attempt in race_condition_retries(
            description=f"fill in the box ID of file {file.id}",
            error_on_failure=lambda: self.FileUpdateError(file_id=file.id),
            logger=log,
        ):
            with attempt:
                try:
                    local_file = await self._file_dao.get_by_id(file.id)
                except ResourceNotFoundError:
                    if file.state in ["cancelled", "failed"]:
                        log.info(
                            "Received event data for a %s FileUpload that FIS doesn't"
                            + " have. This means it probably reached that state before"
                            + " the upload was finished. Ignoring.",
                            file.state,
                            extra={"file_id": file.id},
                        )
                        return
                    log.warning(
                        "Received event for a %s FileUpload that FIS never tracked."
                        + " This is unexpected. Ignoring since there wouldn't be"
                        + " anything for FIS to do anyway.",
                        file.state,
                        extra={"file_id": file.id},
                    )
                    return

                # Fill in a missing box ID even from an old event, which a republish
                #  sends
                if local_file.box_id is None and file.box_id is not None:
                    filled_file = local_file.model_copy(update={"box_id": file.box_id})
                    await self._file_dao.update(
                        filled_file, precondition=_precondition_for(local_file)
                    )
                    local_file = filled_file
                    log.info(
                        "Filled in the missing box ID of file %s.",
                        file.id,
                        extra={"file_id": file.id, "box_id": file.box_id},
                    )

        # Ignore if outdated
        if local_file.state_updated >= file.state_updated:
            log.info("Encountered old data for file %s, ignoring.", file.id)
            return

        # If file state is 'inbox' and the local copy shows interrogation failed, requeue it.
        #  Copies made before 'failed_interrogation' existed still say 'failed'.
        if (
            file.state == "inbox"
            and local_file.state in ("failed", "failed_interrogation")
            and local_file.interrogated
        ):
            await self._requeue_file(file=file.model_copy())
            return

        # If not outdated, see if the state is one we're interested in
        if file.state != local_file.state and file.state in [
            "cancelled",
            "failed",
            "archived",
        ]:
            updated_file = file.model_copy()
            updated_file.can_remove = True
            updated_file.interrogated = (
                local_file.interrogated
            )  # preserve interrogation status
            await self._file_dao.update(updated_file)
            log.info(
                "File %s arrived with state %s. Set can_remove to True.",
                file.id,
                file.state,
            )

    async def _requeue_file(self, *, file: models.FileUnderInterrogation) -> None:
        """Reset a previously failed file so it gets interrogated again.

        Do the following:
        - Delete the stored `InterrogationReport` (log it in the details)
        - Set `file.interrogated` to False
        - Set `file.can_remove` to False
        - Set `file.state` to `"inbox"`
        - Reset the lease fields
        - Update `file.state_updated`
        """
        try:
            await self._interrogation_report_dao.delete(file.id)
            log.info(
                "Discarded InterrogationReport for requeued file %s.",
                file.id,
                extra={"file_id": file.id},
            )
        except ResourceNotFoundError:
            # Log a warning because this is unexpected but could be due to a previous crash
            log.warning(
                "No InterrogationReport found for requeued file %s.",
                file.id,
                extra={"file_id": file.id},
            )

        file.interrogated = False
        file.can_remove = False

        # Clear/reset the lease fields
        file.leased_until = None
        file.leased_by = None
        file.claimed_at = None
        file.times_claimed = 0
        file.state_updated = now_utc_ms_prec()
        await self._file_dao.update(file)
        log.info(
            "File %s was requeued for interrogation.",
            file.id,
            extra={"file_id": file.id},
        )

    async def get_files_not_yet_interrogated(
        self, *, storage_alias: str
    ) -> list[models.BaseFileInformation]:
        """Return up to `MAX_FILES_PER_REQUEST` not-yet-interrogated files for a Data
        Hub (storage_alias), highest priority first.
        """
        files = await self._interrogation_queue.get_waiting_files(
            storage_alias=storage_alias, limit=MAX_FILES_PER_REQUEST
        )
        log.info(
            "Fetched list of %i files for storage_alias %s.", len(files), storage_alias
        )
        return files

    async def claim_file(
        self, *, storage_alias: str, claimant_id: UUID4
    ) -> models.BaseFileInformation | None:
        """Lease the next waiting file of a Data Hub to the caller.

        Files are claimed in this order:
        1. By box priority. All files of the top box go first, then the next box's,
           and so on.
        2. Within a box, files not yet claimed go first. Then come files whose lease
           ran out, earliest first.

        Up to `CLAIM_CANDIDATE_COUNT` files of the top box are read, and one is picked
        at random. That way, claims made at the same time rarely pick the same file.
        Returns `None` if no file is waiting.

        Optimistic locking is used to carry out the database write. In the case of a
        conflict, e.g. the file gets leased to another DHFS instance in the gap between
        read and write, the query is run fresh after a short wait. If this fails
        multiple times, FileClaimError is raised.

        Raises:
        - FileClaimError if other claims keep changing the chosen file first.
        """
        async for attempt in race_condition_retries(
            description=f"claim a file for storage alias {storage_alias}",
            error_on_failure=lambda: self.FileClaimError(storage_alias=storage_alias),
            logger=log,
        ):
            with attempt:
                # Get the candidate pool
                claim_time = now_utc_ms_prec()
                candidates = await self._interrogation_queue.get_claimable_files(
                    storage_alias=storage_alias,
                    claim_time=claim_time,
                    limit=CLAIM_CANDIDATE_COUNT,
                )
                if not candidates:
                    log.debug("No files waiting for storage alias %s.", storage_alias)
                    return None

                # Pick a random file from the pool to reduce contention
                file = random.choice(candidates)  # noqa: S311

                # We don't modify `state_updated` here because
                # A) FIS would then discard the next event and
                # B) Leasing doesn't constitute a state change
                claimed_file = file.model_copy(
                    update={
                        "leased_until": claim_time + timedelta(seconds=LEASE_SECONDS),
                        "leased_by": claimant_id,
                        "claimed_at": claim_time,
                        "times_claimed": file.times_claimed + 1,
                    }
                )
                await self._file_dao.update(
                    claimed_file, precondition=_precondition_for(file)
                )

                log_extra = {
                    "file_id": file.id,
                    "storage_alias": storage_alias,
                    "claimant_id": claimant_id,
                    "times_claimed": claimed_file.times_claimed,
                }
                log.info(
                    "Claimed file %s for claimant %s.",
                    file.id,
                    claimant_id,
                    extra=log_extra,
                )
                if (
                    claimed_file.times_claimed
                    >= self._config.times_claimed_warning_threshold
                ):
                    log.warning(
                        "File %s has been claimed %i times without being interrogated.",
                        file.id,
                        claimed_file.times_claimed,
                        extra=log_extra,
                    )
                return models.BaseFileInformation(**claimed_file.model_dump())

        # Not reached, since the loop raises this after the last try, but mypy can't tell
        raise self.FileClaimError(storage_alias=storage_alias)

    async def delete_file(self, *, file_id: UUID4) -> None:
        """Delete a file and its interrogation report (if any) from the database.

        This removes the entries from the database as a result of an upstream
        deletion in UCS. The usual cause for this is the replacement of a failed or
        cancelled FileUpload with a new instance for the same file alias.

        If no matching entry is found, it is assumed that the entry was already deleted.
        """
        with suppress(ResourceNotFoundError):
            await self._interrogation_report_dao.delete(file_id)
            log.info("Interrogation report deleted for file ID %s.", file_id)

        try:
            await self._file_dao.delete(file_id)
            log.info("Local copy deleted for file ID %s.", file_id)
        except ResourceNotFoundError:
            log.info("Did not find file with ID %s; presumed already deleted.", file_id)

    async def store_upload_box_priority(
        self, *, priority: models.UploadBoxPriority
    ) -> None:
        """Store the upload box priority list.

        Ignore the list if its version is not higher than the stored one's.
        """
        with suppress(ResourceNotFoundError):
            stored_priority = await self._upload_box_priority_dao.get_by_id(priority.id)
            if priority.version <= stored_priority.version:
                log.info(
                    "Ignored upload box priority version %i because it appears to be old.",
                    priority.version,
                )
                return

        await self._upload_box_priority_dao.upsert(priority)
        log.info(
            "Stored upload box priority version %i with %i boxes.",
            priority.version,
            len(priority.entries),
        )

    async def clear_upload_box_priority(self, *, priority_id: str) -> None:
        """Empty the stored upload box priority list, keeping its version.

        Keeping the version stops a replayed older event from restoring the list.
        If no list is stored, do nothing.
        """
        try:
            stored_priority = await self._upload_box_priority_dao.get_by_id(priority_id)
        except ResourceNotFoundError:
            log.info("Received a deleted upload box priority list, but none is stored.")
            return

        await self._upload_box_priority_dao.update(
            stored_priority.model_copy(update={"entries": []})
        )
        log.warning(
            "Received a deleted upload box priority list, which RS never deletes."
            + " Emptied the stored list and kept version %i.",
            stored_priority.version,
        )
