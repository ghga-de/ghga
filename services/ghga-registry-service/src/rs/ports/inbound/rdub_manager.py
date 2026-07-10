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

"""Port definition for the RDUBManager."""

from abc import ABC, abstractmethod

from ghga_service_commons.auth.ghga import AuthContext
from ghga_service_commons.utils.utc_dates import UTCDatetime
from pydantic import UUID4, PositiveInt

from rs.core.models import (
    PID,
    BoxRetrievalResults,
    BoxUploadsPage,
    FileUploadBox,
    GrantId,
    GrantWithBoxInfo,
    ResearchDataUploadBox,
    UploadBoxState,
)


class RDUBManagerPort(ABC):
    """Port for a class that executes operations surrounding ResearchDataUploadBoxes"""

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
        """Raised when an operation fails for a reason directly related to the accession
        map.

        `error_type` is always set and indicates the specific failure:
        - "archived": box is already archived; no item lists populated.
        - "duplicate_file_ids": a file ID appears more than once; `affected_file_ids`
          contains the duplicated IDs.
        - "unknown_file_ids": map references file IDs not present in the box;
          `affected_file_ids` contains them.
        - "unmapped_file_ids": active box files are absent from the map;
          `affected_file_ids` contains them.
        - "accession_conflict": accessions already mapped to different file IDs or
          attributed to a different study; `conflicting_accessions` contains them.
        - "unknown_accessions": accessions not registered yet (no unmapped entry);
          `unknown_accessions` contains them.
        """

        def __init__(
            self,
            message: str = "",
            *,
            error_type: str,
            conflicting_accessions: list[str] | None = None,
            unknown_accessions: list[str] | None = None,
            affected_file_ids: list[str] | None = None,
        ) -> None:
            self.error_type = error_type
            self.conflicting_accessions = conflicting_accessions or []
            self.unknown_accessions = unknown_accessions or []
            self.affected_file_ids = affected_file_ids or []
            super().__init__(message)

    class ArchivalPrereqsError(RuntimeError):
        """Raised when the pre-requisites for box archival are not met."""

    class BoxVersionError(RuntimeError):
        """Raised when changes to a resource can't be made because the request
        references a version of the resource that is not current.
        """

    class BoxIncompleteUploadsError(RuntimeError):
        """Raised when locking is rejected because files have incomplete uploads."""

        def __init__(self, *, incomplete_file_ids: list[UUID4]):
            self.incomplete_file_ids = incomplete_file_ids
            super().__init__(f"{len(incomplete_file_ids)} file(s) are incomplete.")

    class BoxTitleExistsError(RuntimeError):
        """Raised when trying to create an upload box with a title that already
        exists.
        """

    class BoxMaxSizeTooLowError(RuntimeError):
        """Raised when the requested max_size is smaller than the bytes already
        uploaded.
        """

    class BoxStateError(RuntimeError):
        """Raised when an operation is incompatible with the box's current state
        (e.g. an archived box cannot be deleted).
        """

        def __init__(self, *, operation: str, state: UploadBoxState):
            self.state = state
            super().__init__(f"Cannot {operation} because the box state is '{state}'.")

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
        max_size: PositiveInt,
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
            BoxTitleExistsError: If a box with the given title already exists.
            OperationError: If there's a problem creating a corresponding FileUploadBox.
        """
        ...

    @abstractmethod
    async def update_research_data_upload_box(  # noqa: PLR0913
        self,
        *,
        box_id: UUID4,
        version: int,
        title: str | None,
        description: str | None,
        auth_context: AuthContext,
        state: UploadBoxState | None = None,
        max_size: PositiveInt | None = None,
        force: bool = False,
    ) -> None:
        """Update a research data upload box.

        Raises:
            BoxNotFoundError: If the research data upload box doesn't exist.
            BoxAccessError: If the user doesn't have access to the research data
                upload box.
            BoxVersionError: If the requested ResearchDataUploadBox version is outdated
                or the FileUploadBox version is outdated when updating the
                FileUploadBox.
            StateChangeError: If the requested state transition is invalid.
            OperationError: If there's a problem updating the corresponding
                FileUploadBox.
            ArchivalPrereqsError: If trying to archive the box and prerequisites
                aren't met.
            BoxSizeTooSmallError: If the new max_size is smaller than bytes already
                uploaded.
            ValueError: If state and max_size are both specified.
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
    ) -> GrantId:
        """Grant upload access to a user for a specific research data upload box.

        Returns the created grant ID.

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
        skip: int = 0,
        limit: int | None = None,
        sort: list[str] | None = None,
    ) -> BoxUploadsPage:
        """Get a page of file uploads for a research data upload box.

        `skip`, `limit`, and `sort` are forwarded to the file box service's paginated
        endpoint. `sort` is a list of FileUpload field names to sort by, each optionally
        prefixed with a dash to denote descending order; when omitted, the file box
        service's default ordering (by alias) is used.
        Returns a BoxUploadsPage with the page's file uploads and the total unpaginated
        count.
        It is assumed that `skip`, `limit`, and `sort` are validated beforehand - they
        are not validated in this method.

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
    async def delete_file_upload(
        self,
        *,
        box_id: UUID4,
        file_id: UUID4,
        auth_context: AuthContext,
    ) -> None:
        """Delete a FileUpload from an upload box.

        Requires either the Data Steward role or upload access to the box.

        Raises:
            BoxNotFoundError: If the box doesn't exist.
            BoxAccessError: If the user doesn't have access to the box.
            BoxStateError: If the box is locked.
            OperationError: If there's a problem communicating with the file box
                service.
        """
        ...

    @abstractmethod
    async def delete_research_data_upload_box(
        self,
        *,
        box_id: UUID4,
        version: int,
        user_id: UUID4,
    ) -> None:
        """Delete a ResearchDataUploadBox and its corresponding FileUploadBox.

        The RDUB (and FUB) must be not be in the 'archived' state.
        The version must match what is in the database.

        First, the file list is retrieved from UCS. Then any corresponding file
        accession mappings are deleted from UCS. Then the FileUploadBox and associated
        FileUploads are deleted, followed by any valid upload grants, and finally the
        ResearchDataUploadBox.

        Raises:
            BoxNotFoundError: If the box doesn't exist.
            BoxVersionError: If the requested ResearchDataUploadBox version is outdated,
                or the associated FileUploadBox version is outdated.
            BoxStateError: If the box is archived and cannot be deleted.
            OperationError: If there's a problem communicating with the file box
                service.
        """
        ...

    @abstractmethod
    async def store_accession_map(
        self,
        *,
        box_id: UUID4,
        box_version: int,
        accession_map: dict[PID, UUID4],
        study_id: PID,
    ) -> None:
        """Update the file accession map for a given box and publish an outbox event.
        This results in a version increment for the ResearchDataUploadBox.

        **Files with a state of *cancelled* or *failed* are ignored.**

        Check the specified ResearchDataUploadBox to verify it exists, that the version
        stated in the request is current, and the box has not already been archived.

        Next, check the mapping to verify that every file ID is specified exactly
        once (and thus mapping is 1:1). This does not mean that the mapping contains
        all accessions in the study, just all the accessions associated with the upload
        box.

        Then retrieve the latest list of files in the box from the File Box API to
        verify that:
        - each file ID in the mapping exists in the retrieved list of files
        - all file IDs in the box are included in the mapping

        Finally, submit the accession map to the file controller and update the RDUB
        version.

        Raises:
            BoxNotFoundError: If the box doesn't exist
            BoxVersionError: If the requested ResearchDataUploadBox version is outdated
            AccessionMapError: In all cases `error_type` is set. See the class
            docstring for the full mapping of `error_type` values to populated fields.
            Raised when the box is archived, any file IDs are duplicated, unknown, or
            unmapped, or any accessions conflict with existing immutable mappings.
        """
        ...
