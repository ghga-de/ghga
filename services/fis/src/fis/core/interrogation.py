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

"""Core logic managing FileUnderInterrogation objects and interpreting
InterrogationReports.
"""

import logging
from contextlib import suppress

from hexkit.utils import now_utc_ms_prec
from pydantic import UUID4

from fis.config import Config
from fis.core import models
from fis.ports.inbound.interrogation import InterrogationHandlerPort
from fis.ports.outbound.dao import (
    FileDao,
    InterrogationReportDao,
    MultipleHitsFoundError,
    NoHitsFoundError,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
)
from fis.ports.outbound.event_pub import EventPubTranslatorPort
from fis.ports.outbound.secrets import SecretsClientPort

STATES = models.FileUploadState
log = logging.getLogger(__name__)


class InterrogationHandler(InterrogationHandlerPort):
    """This is the core class that manages `FileUnderInterrogation` and
    `InterrogationReport` objects.
    """

    def __init__(
        self,
        *,
        config: Config,
        file_dao: FileDao,
        interrogation_report_dao: InterrogationReportDao,
        event_publisher: EventPubTranslatorPort,
        secrets_client: SecretsClientPort,
    ):
        self._config = config
        self._file_dao = file_dao
        self._interrogation_report_dao = interrogation_report_dao
        self._publisher = event_publisher
        self._secrets_client = secrets_client

    async def check_if_removable(self, *, object_id: UUID4) -> bool:
        """Return `True` if an object can be removed from the interrogation bucket and
        `False` otherwise.
        """
        try:
            file = await self._file_dao.find_one(mapping={"object_id": object_id})
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

        In both cases, set `interrogated=True`, `state="interrogated"`, and
        `state_updated=now()` for the `FileUnderInterrogation` event. In the case of
        interrogation failure, also set `can_remove=True`.

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
            # See if the reports differ - the timestamps are immaterial here
            report_subset = report.model_dump(exclude={"interrogated_at", "secret"})
            stored_subset = stored_report.model_dump(exclude={"interrogated_at"})
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
            else:
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
        # Store DB copy of report
        await self._interrogation_report_dao.insert(
            models.InterrogationReport(**report.model_dump(exclude={"secret"}))
        )
        log.debug("Stored InterrogationReport for file %s", file.id)

        # If everything goes well, update the FileUnderInterrogation in the DB
        updated_file = file.model_copy(deep=True)
        updated_file.state = "failed"
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
            reason=report.reason,
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
        # Deposit the secret with the EKSS
        try:
            secret_id = await self._secrets_client.deposit_secret(secret=report.secret)
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
            updated_file.object_id = report.object_id
            updated_file.bucket_id = report.bucket_id
            updated_file.encrypted_size = report.encrypted_size
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
                bucket_id=report.bucket_id,
                object_id=report.object_id,
                interrogated_at=report.interrogated_at,
                encrypted_parts_md5=report.encrypted_parts_md5,
                encrypted_parts_sha256=report.encrypted_parts_sha256,
                encrypted_size=report.encrypted_size,
            )
            log.info(
                "Successfully processed success report for file %s.", report.file_id
            )

    async def process_file_upload(self, *, file: models.FileUnderInterrogation) -> None:
        """Process a newly received file upload.

        Make sure we don't already have this file. If we don't, then add it to the DB.
        If we do, see if this information is old or new. If old, ignore it.
        If the received information is newer than what we have, and the state is
        different, *and* the new state represents one of the end states, then update our
        copy.

        We don't track files that are only in the 'init' state, we only track them once
        they reach 'inbox'. The transition from 'inbox' to 'interrogated' or from 'inbox'
        to 'failed' is performed by the FIS in `.handle_interrogation_report()`. The
        state 'awaiting_archival' is not of interest of the FIS and has no functional
        difference from 'interrogated' from the perspective of the FIS. Therefore, the
        only states of interest in this method are 'cancelled', 'failed', and 'archived'.
        """
        if file.state == "init":
            return
        elif file.state == "inbox":
            with suppress(ResourceAlreadyExistsError):
                await self._file_dao.insert(file)
                return

        # If we make it past that block, then it is not new and we must compare.
        local_file = await self._file_dao.get_by_id(file.id)

        # Ignore if outdated
        if local_file.state_updated >= file.state_updated:
            log.info("Encountered old data for file %s, ignoring.", file.id)
            return

        # If not outdated, see if the state is one we're interested in
        if file.state != local_file.state and file.state in [
            "cancelled",
            "failed",
            "archived",
        ]:
            file.can_remove = True
            file.interrogated = local_file.interrogated  # preserve interrogation status
            await self._file_dao.update(file)
            log.info(
                "File %s arrived with state %s. Set can_remove to True.",
                file.id,
                file.state,
            )

    async def get_files_not_yet_interrogated(
        self, *, storage_alias: str
    ) -> list[models.BaseFileInformation]:
        """Return a list of not-yet-interrogated files for a Data Hub (storage_alias)"""
        files = [
            models.BaseFileInformation(**x.model_dump())
            async for x in self._file_dao.find_all(
                mapping={
                    "storage_alias": storage_alias,
                    "state": "inbox",
                    "interrogated": False,
                }
            )
        ]
        log.info(
            "Fetched list of %i files for storage_alias %s.", len(files), storage_alias
        )
        return files

    async def ack_file_cancellation(self, *, file_id: UUID4) -> None:
        """Acknowledge the removal or cancellation of a FileUpload.

        Raises:
        - FileNotFoundError if there's no file with the ID specified in the report.
        """
        # First make sure we have this file
        try:
            file = await self._file_dao.get_by_id(file_id)
        except ResourceNotFoundError as err:
            log.error(
                "Can't acknowledge file cancellation because no file with ID %s exists.",
                file_id,
            )
            raise self.FileNotFoundError(file_id=file_id) from err

        file.state = "cancelled"
        file.state_updated = now_utc_ms_prec()
        file.can_remove = True

        await self._file_dao.update(file)
        log.info("Acknowledged file cancellation for %s", file_id)
