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

"""Describes a class for managing FileUnderInterrogation objects and interpreting
InterrogationReports.
"""

from abc import ABC, abstractmethod

from pydantic import UUID4

from fis.core import models


class InterrogationHandlerPort(ABC):
    """This is the core class that manages `FileUnderInterrogation` and
    `InterrogationReport` objects.
    """

    class FileNotFoundError(RuntimeError):
        """Raised when a file cannot be found in the database"""

        def __init__(self, *, file_id: UUID4):
            msg = f"The file with the ID {file_id} does not exist."
            super().__init__(msg)

    class SecretDepositionError(RuntimeError):
        """Raised when there's a problem depositing a new file encryption secret with
        the EKSS.
        """

        def __init__(self, *, file_id: UUID4, reason: str):
            msg = (
                f"Failed to deposit encryption secret for file with the ID {file_id}."
                + f" Reason: {reason}"
            )
            super().__init__(msg)

    class InterrogationReportConflict(RuntimeError):
        """Raised when a submitted InterrogationReport conflicts with the database state."""

        def __init__(self, *, file_id: UUID4):
            msg = (
                f"File {file_id} has already been interrogated, but the new"
                + " InterrogationReport contradicts what is stored in the database."
            )
            super().__init__(msg)

    @abstractmethod
    async def check_if_removable(self, *, object_id: UUID4) -> bool:
        """Return `True` if an object can be removed from the interrogation bucket and
        `False` otherwise.
        """

    @abstractmethod
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
        """

    @abstractmethod
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

    @abstractmethod
    async def get_files_not_yet_interrogated(
        self, *, storage_alias: str
    ) -> list[models.BaseFileInformation]:
        """Return a list of not-yet-interrogated files for a Data Hub"""

    @abstractmethod
    async def ack_file_cancellation(self, *, file_id: UUID4) -> None:
        """Acknowledge the removal or cancellation of a FileUpload.

        Raises:
        - FileNotFoundError if there's no file with the ID specified in the report.
        """
