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

"""Port definition for the Upload Orchestrator."""

from abc import ABC, abstractmethod

from ghga_service_commons.auth.ghga import AuthContext
from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import UUID4

from uos.core.models import (
    AccessionMapRequest,
    BoxRetrievalResults,
    FileUploadBox,
    FileUploadWithAccession,
    GrantWithBoxInfo,
    ResearchDataUploadBox,
    UpdateUploadBoxRequest,
    UploadBoxState,
)


class UploadOrchestratorPort(ABC):
    """Port for the Upload Orchestrator service."""

    class BoxAccessError(RuntimeError):
        """Raised when a ResearchDataUploadBox cannot be accessed."""

    class BoxNotFoundError(RuntimeError):
        """Raised when a ResearchDataUploadBox is not found in the DB."""

        def __init__(self, *, box_id: UUID4):
            msg = f"The ResearchDataUploadBox with ID {box_id} was not found in the DB."
            super().__init__(msg)

    class GrantNotFoundError(RuntimeError):
        """Raised when unable to revoke a grant because it doesn't exist."""

        def __init__(self, *, grant_id: UUID4) -> None:
            msg = f"Failed to revoke grant {grant_id} because it doesn't exist."
            super().__init__(msg)

    class AccessionMapError(RuntimeError):
        """Raised when an operation fails for a reason directly related to the accession map."""

    class ArchivalPrereqsError(RuntimeError):
        """Raised when the pre-requisites for box archival are not met."""

    class VersionError(RuntimeError):
        """Raised when changes to a resource can't be made because the request
        references a version of the resource that is not current.
        """

    class StateChangeError(RuntimeError):
        """Raised when there is an attempt to make an invalid state change for
        a Research Data Upload Box.
        """

        def __init__(self, *, old_state: UploadBoxState, new_state: UploadBoxState):
            msg = (
                f"Research Data Upload Boxes cannot be changed from '{old_state}'"
                + f" to '{new_state}'."
            )
            super().__init__(msg)

    @abstractmethod
    async def create_research_data_upload_box(
        self,
        *,
        title: str,
        description: str,
        storage_alias: str,
        data_steward_id: UUID4,
    ) -> UUID4:
        """Create a new research data upload box.

        This operation:
        1. Creates a FileUploadBox in the service that owns them
        2. Creates a ResearchDataUploadBox locally
        3. Emits events and audit records

        Returns:
            The UUID of the newly created research data upload box

        Raises:
            OperationError: If there's a problem creating a corresponding FileUploadBox.
        """
        ...

    @abstractmethod
    async def update_research_data_upload_box(
        self,
        *,
        box_id: UUID4,
        request: UpdateUploadBoxRequest,
        auth_context: AuthContext,
    ) -> None:
        """Update a research data upload box.

        Raises:
            BoxNotFoundError: If the research data upload box doesn't exist.
            BoxAccessError: If the user doesn't have access to the research data upload box.
            VersionError: If the requested ResearchDataUploadBox version is outdated or
                the FileUploadBox version is outdated when updating the FileUploadBox.
            StateChangeError: If the requested state transition is invalid.
            OperationError: If there's a problem updating the corresponding FileUploadBox.
            ArchivalPrereqsError: If trying to archive the box and prerequisites aren't met.
        """
        ...

    @abstractmethod
    async def grant_upload_access(  # noqa: PLR0913
        self,
        *,
        user_id: UUID4,
        iva_id: UUID4,
        box_id: UUID4,
        valid_from: UTCDatetime,
        valid_until: UTCDatetime,
        granting_user_id: UUID4,
    ) -> None:
        """Grant upload access to a user for a specific research data upload box.

        Raises:
            AccessAPIError: if there's a problem communicating with the access API.
            BoxNotFoundError: If the box doesn't exist.
        """
        ...

    @abstractmethod
    async def revoke_upload_access_grant(self, grant_id: UUID4) -> None:
        """Revoke a user's access to an upload box.

        Raises:
            GrantNotFoundError: if the grant wasn't found in the access API.
            AccessAPIError: if there's a problem communicating with the access API.
        """
        ...

    @abstractmethod
    async def get_upload_access_grants(
        self,
        *,
        user_id: UUID4 | None = None,
        iva_id: UUID4 | None = None,
        box_id: UUID4 | None = None,
        valid: bool | None = None,
    ) -> list[GrantWithBoxInfo]:
        """Get a list of upload grants with the associated box titles and descriptions.
        Results are sorted by validity, user ID, IVA ID, box ID, and grant ID.

        Raises:
            AccessAPIError: If there's a problem communicating with the access API.
        """
        ...

    @abstractmethod
    async def get_upload_box_files(
        self,
        *,
        box_id: UUID4,
        auth_context: AuthContext,
    ) -> list[FileUploadWithAccession]:
        """Get list of file uploads for a research data upload box.

        Returns a list of file uploads in the upload box.

        Raises:
            BoxNotFoundError: If the box doesn't exist.
            BoxAccessError: If the user doesn't have access to the box.
            OperationError: If there's a problem querying the file box service.
            AccessAPIError: If there's a problem querying the access api
        """
        ...

    @abstractmethod
    async def upsert_file_upload_box(self, file_upload_box: FileUploadBox) -> None:
        """Handle FileUploadBox update events from file box service.

        Updates the corresponding ResearchDataUploadBox with latest file count and size.
        """

    @abstractmethod
    async def get_research_data_upload_box(
        self, *, box_id: UUID4, auth_context: AuthContext
    ) -> ResearchDataUploadBox:
        """Retrieve a Research Data Upload Box by ID.

        For regular users, the access api will be queried. For Data Stewards, this check
        is skipped.

        Raises:
            BoxAccessError: If the user doesn't have access to the box
            BoxNotFoundError: If the box doesn't exist
            AccessAPIError: If there's a problem querying the access api
        """
        ...

    @abstractmethod
    async def get_research_data_upload_boxes(
        self,
        *,
        auth_context: AuthContext,
        skip: int | None = None,
        limit: int | None = None,
        state: UploadBoxState | None = None,
    ) -> BoxRetrievalResults:
        """Retrieve all Research Data Upload Boxes, optionally paginated.

        For data stewards, returns all boxes. For regular users, only returns boxes
        they have access to according to the Access API.

        Results are sorted first by state ("open" first), then by most
        recently changed, and then by box ID. Results can also be filtered to show boxes
        with a chosen state.

        Returns a BoxRetrievalResults instance with the boxes and unpaginated count.
        """
        ...

    @abstractmethod
    async def update_accession_map(
        self, *, box_id: UUID4, request: AccessionMapRequest
    ) -> None:
        """Update the file accession map for a given box and publish an outbox event.
        This results in a version increment for the ResearchDataUploadBox.

        **Files with a state of *cancelled* or *failed* are ignored.**

        Check the specified ResearchDataUploadBox to verify it exists, that the version
        stated in the request is current, and that the box has not already been archived.

        Next, checked the mapping to verify that every file ID is specified exactly
        once (and thus mapping is 1:1).

        Then retrieve the latest list of files in the box from the File Box API to
        verify that:
        - each file ID in the mapping exists in the retrieved list of files
        - all file IDs in the box are included in the mapping

        Finally, store the mapping in the DB and publish an outbox event containing
        the mapping field content.

        Raises:
            BoxNotFoundError: If the box doesn't exist
            VersionError: If the requested ResearchDataUploadBox version is outdated
            AccessionMapError: If
            - the box is already archived, or
            - the accession map includes a file ID that doesn't exist in the box, or
            - any files are specified more than once, or
            - any files in the box are left unmapped, or
            - an unexpected database error occurs while upserting the accession map.
        """
        ...
