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

"""Logic for creating and managing ResearchDataUploadBoxes."""

import logging
from collections import Counter
from typing import Any
from uuid import UUID

from ghga_service_commons.auth.ghga import AuthContext
from ghga_service_commons.utils.utc_dates import UTCDatetime
from hexkit.protocols.dao import NoHitsFoundError, ResourceNotFoundError
from hexkit.utils import now_utc_ms_prec
from pydantic import UUID4, PositiveInt

from rs.constants import VALID_STATE_TRANSITIONS
from rs.core.models import (
    PID,
    BoxRetrievalResults,
    FileAccession,
    FileUploadBox,
    FileUploadWithAccession,
    GrantId,
    GrantWithBoxInfo,
    ResearchDataUploadBox,
    UploadBoxState,
)
from rs.ports.inbound.files import FileControllerPort
from rs.ports.inbound.rdub_manager import RDUBManagerPort
from rs.ports.outbound.audit import AuditRepositoryPort
from rs.ports.outbound.dao import BoxDao
from rs.ports.outbound.http import AccessClientPort, FileBoxClientPort

log = logging.getLogger(__name__)

__all__ = ["RDUBManager"]


def is_data_steward(auth_context: AuthContext) -> bool:
    """Returns a bool indicating if the auth context is for a Data Steward"""
    return "data_steward" in auth_context.roles


class RDUBManager(RDUBManagerPort):
    """A class for executing operations surrounding ResearchDataUploadBoxes"""

    def __init__(
        self,
        *,
        box_dao: BoxDao,
        file_controller: FileControllerPort,
        audit_repository: AuditRepositoryPort,
        file_upload_box_client: FileBoxClientPort,
        access_client: AccessClientPort,
    ):
        self._box_dao = box_dao
        self._file_controller = file_controller
        self._audit_repository = audit_repository
        self._file_upload_box_client = file_upload_box_client
        self._access_client = access_client

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
        # Title uniqueness check is done this way instead of via unique index to avoid
        #  chicken-egg problem with dependent FUB-RDUB creation
        if [x async for x in self._box_dao.find_all(mapping={"title": title})]:
            log.error(
                "ResearchDataUploadBox creation failed because a box with the title %s"
                + " already exists.",
                title,
            )
            raise self.BoxTitleExistsError()

        # Create FileUploadBox in external service
        file_upload_box_id = await self._file_upload_box_client.create_file_upload_box(
            storage_alias=storage_alias, max_size=max_size
        )

        # Create ResearchDataUploadBox
        box = ResearchDataUploadBox(
            version=0,
            state="open",
            title=title,
            description=description,
            last_changed=now_utc_ms_prec(),
            changed_by=data_steward_id,
            file_upload_box_id=file_upload_box_id,
            file_upload_box_version=0,
            file_upload_box_state="open",
            storage_alias=storage_alias,
            max_size=max_size,
        )

        # Store in repository & create audit record
        await self._box_dao.insert(box)
        await self._audit_repository.log_box_created(box=box, user_id=data_steward_id)
        return box.id

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
            BoxAccessError: If the user doesn't have access to the research data upload box.
            BoxVersionError: If the requested ResearchDataUploadBox version is outdated or
                the FileUploadBox version is outdated when updating the FileUploadBox.
            StateChangeError: If the requested state transition is invalid.
            OperationError: If there's a problem updating the corresponding FileUploadBox.
            ArchivalPrereqsError: If trying to archive the box and prerequisites aren't met.
            ValueError: If state and max_size are both specified.
        """
        if state is not None and max_size is not None:
            raise ValueError("Cannot specify both state and max_size in same call")

        # Get existing box if user has access to it
        box = await self.get_research_data_upload_box(
            box_id=box_id, auth_context=auth_context
        )

        # Make sure the request is not based on outdated info
        if box.version != version:
            log.error(
                "Can't update RDUB %s because the request is outdated.",
                box_id,
                extra={
                    "box_id": box_id,
                    "current_version": box.version,
                    "requested_version": version,
                },
            )
            raise self.BoxVersionError(f"Research Data Upload Box {box_id} has changed")

        update = {
            "title": title,
            "description": description,
            "state": state,
            "max_size": max_size,
        }
        changed_fields = {k: v for k, v in update.items() if v and getattr(box, k) != v}
        if not changed_fields:
            log.info(
                "RDUB update request for box %s did not contain any changes.", box_id
            )
            return

        # If not a data steward, the only acceptable update is to move from OPEN to LOCKED
        is_ds = is_data_steward(auth_context)
        if not is_ds and not (
            changed_fields == {"state": "locked"} and box.state == "open"
        ):
            raise self.BoxAccessError("Unauthorized")

        # Update fields on the research data upload box instance
        updated_box = box.model_copy(update=changed_fields)
        user_id = UUID(auth_context.id)
        updated_box.changed_by = user_id
        updated_box.last_changed = now_utc_ms_prec()
        updated_box.version += 1

        if "state" in changed_fields:
            await self._apply_state_update(
                box=box, updated_box=updated_box, user_id=user_id, force=force
            )
        elif "max_size" in changed_fields:
            await self._apply_max_size_update(
                box=box, updated_box=updated_box, user_id=user_id
            )
        else:
            await self._apply_metadata_update(updated_box=updated_box, user_id=user_id)

    def _check_state_change_is_valid(
        self, *, old_state: UploadBoxState, new_state: UploadBoxState
    ) -> None:
        """Verify that the new state value for a box represents a valid transition.

        Raises:
            StateChangeError: If the state transition is invalid.
        """
        if (old_state, new_state) not in VALID_STATE_TRANSITIONS:
            raise self.StateChangeError(old_state=old_state, new_state=new_state)

    async def _handle_state_change(
        self,
        *,
        old_box: ResearchDataUploadBox,
        updated_box: ResearchDataUploadBox,
        force: bool = False,
    ) -> None:
        """Handle state change for a Research Data Upload Box and the corresponding
        FileUploadBox.
        """
        rdub_id = updated_box.id
        fub_id = updated_box.file_upload_box_id
        match (old_box.state, updated_box.state):
            case ("open", "locked"):  # lock the box
                try:
                    await self._file_upload_box_client.lock_file_upload_box(
                        box_id=fub_id,
                        version=old_box.file_upload_box_version,
                        force=force,
                    )
                except FileBoxClientPort.FUBIncompleteUploadsError as incomplete_err:
                    raise self.BoxIncompleteUploadsError(
                        incomplete_file_ids=incomplete_err.incomplete_file_ids
                    ) from incomplete_err
            case ("locked", "open"):  # unlock the box
                if force:
                    log.debug(
                        "force=True is ignored for locked->open state changes on RDUB %s",
                        rdub_id,
                    )
                await self._file_upload_box_client.unlock_file_upload_box(
                    box_id=fub_id, version=old_box.file_upload_box_version
                )
            case ("locked", "archived"):  # archive the box
                if force:
                    log.debug(
                        "force=True is ignored for locked->archived state changes on RDUB %s",
                        rdub_id,
                    )
                # Check prerequisites using old version number for logging purposes
                await self._check_archival_prerequisites(box=old_box)

                # Use old box data because `updated_box` has already been, well, updated
                try:
                    await self._file_upload_box_client.archive_file_upload_box(
                        box_id=fub_id,
                        version=old_box.file_upload_box_version,
                    )
                except FileBoxClientPort.FUBVersionError as version_err:
                    log.error(
                        "Can't archive RDUB %s because the associated FileUploadBox"
                        + " version has changed.",
                        rdub_id,
                        extra={
                            "box_id": rdub_id,
                            "file_upload_box_id": fub_id,
                            "request_file_upload_box_version": old_box.file_upload_box_version,
                        },
                    )
                    raise self.BoxVersionError(
                        f"File Upload Box {fub_id} version is out of date."
                    ) from version_err
            case _:
                # maybe we allowed a new state change but forgot to handle it here?
                raise NotImplementedError()

    async def _check_archival_prerequisites(
        self, *, box: ResearchDataUploadBox
    ) -> None:
        """Check prerequisites for archiving a research data upload box.

        Raises:
            ArchivalPrereqsError: If there are any files in the box that don't yet have
                an accession assigned OR if the box is still in the 'open' state.
            OperationError: If there's a problem querying the file box service.
        """
        box_id = box.id

        # Get files list from File Box API - this always gets the latest data
        files = await self._file_upload_box_client.get_file_upload_list(
            box_id=box.file_upload_box_id
        )

        if not files:
            # No files in box, nothing to check
            return

        # Make sure all files have an accession number
        file_ids_in_box = {f.id for f in files}
        accessions = await self._file_controller.get_accessions_by_file_ids(
            file_ids=file_ids_in_box
        )
        mapped_file_ids = {fid for fid in accessions}
        unassigned_files = file_ids_in_box - mapped_file_ids

        if unassigned_files:
            log.error(
                "Can't archive RDUB %s because not all files have been assigned an accession.",
                box_id,
                extra={
                    "box_id": box_id,
                    "version": box.version,
                    "file_ids": unassigned_files,
                },
            )
            raise self.ArchivalPrereqsError(
                f"The following files are missing an accession: {unassigned_files}"
            )

    async def _apply_metadata_update(
        self,
        *,
        updated_box: ResearchDataUploadBox,
        user_id: UUID,
    ) -> None:
        """Persist a title/description-only change and write the audit record."""
        await self._box_dao.update(updated_box)
        await self._audit_repository.log_box_updated(box=updated_box, user_id=user_id)

    async def _apply_max_size_update(
        self,
        *,
        box: ResearchDataUploadBox,
        updated_box: ResearchDataUploadBox,
        user_id: UUID,
    ) -> None:
        """Resize the FileUploadBox, persist the change, and write the audit record.

        Rolls back the local DAO write and re-raises on any client error.

        Raises:
            BoxVersionError: FUB version is out of date.
            BoxMaxSizeTooLowError: New max_size is smaller than bytes already uploaded.
        """
        updated_box.file_upload_box_version += 1
        await self._box_dao.update(updated_box)
        try:
            await self._file_upload_box_client.resize_file_upload_box(
                box_id=box.file_upload_box_id,
                version=box.file_upload_box_version,
                max_size=updated_box.max_size,
            )
        except FileBoxClientPort.FUBVersionError as version_err:
            log.error(
                "Can't resize FUB %s for RDUB %s because the FUB version is out of date.",
                box.file_upload_box_id,
                box.id,
                extra={
                    "box_id": box.id,
                    "file_upload_box_id": box.file_upload_box_id,
                    "file_upload_box_version": box.file_upload_box_version,
                },
            )
            await self._box_dao.update(box)
            raise self.BoxVersionError(
                f"File Upload Box {box.file_upload_box_id} version is out of date."
            ) from version_err
        except FileBoxClientPort.FUBMaxSizeTooLowError as size_err:
            log.error(
                "Can't resize FUB %s for RDUB %s because the new max_size is smaller"
                + " than the bytes already uploaded.",
                box.file_upload_box_id,
                box.id,
                extra={
                    "box_id": box.id,
                    "file_upload_box_id": box.file_upload_box_id,
                    "max_size": updated_box.max_size,
                },
            )
            await self._box_dao.update(box)
            raise self.BoxMaxSizeTooLowError(str(size_err)) from size_err
        except Exception:
            log.warning(
                "Failed to resize FUB %s, rolling back changes for RDUB %s",
                box.file_upload_box_id,
                box.id,
            )
            await self._box_dao.update(box)
            raise
        else:
            await self._audit_repository.log_box_updated(
                box=updated_box, user_id=user_id
            )

    async def _apply_state_update(
        self,
        *,
        box: ResearchDataUploadBox,
        updated_box: ResearchDataUploadBox,
        user_id: UUID,
        force: bool = False,
    ) -> None:
        """Validate the state transition, persist, dispatch _handle_state_change, and audit.

        Rolls back the local DAO write on failure.

        Raises:
            StateChangeError: The requested transition is not in VALID_STATE_TRANSITIONS.
            BoxVersionError: FUB version is out of date.
            ArchivalPrereqsError: Archival prerequisites not met.
        """
        self._check_state_change_is_valid(
            old_state=box.state, new_state=updated_box.state
        )
        updated_box.file_upload_box_state = updated_box.state
        updated_box.file_upload_box_version += 1
        await self._box_dao.update(updated_box)
        try:
            await self._handle_state_change(
                old_box=box, updated_box=updated_box, force=force
            )
        except Exception:
            log.warning(
                "Failed to update FUB %s, rolling back changes for RDUB %s",
                box.file_upload_box_id,
                box.id,
            )
            await self._box_dao.update(box)
            raise
        else:
            await self._audit_repository.log_box_updated(
                box=updated_box, user_id=user_id
            )

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
        # TODO: Should we block access to archived boxes, or let that be handled IRL?
        # Verify the upload box exists
        await self._box_dao.get_by_id(box_id)

        # Grant access via Claims Repository Service (errors handled by access client)
        grant_id = await self._access_client.grant_upload_access(
            user_id=user_id,
            iva_id=iva_id,
            box_id=box_id,
            valid_from=valid_from,
            valid_until=valid_until,
        )
        await self._audit_repository.log_access_granted(
            box_id=box_id, grantor_id=granting_user_id, grantee_id=user_id
        )
        log.info(
            "Access grant operation successful for user %s and box %s", user_id, box_id
        )
        return grant_id

    async def revoke_upload_access_grant(self, grant_id: UUID4) -> None:
        """Revoke a user's access to an upload box.

        Raises:
            GrantNotFoundError: if the grant wasn't found in the access API.
            AccessAPIError: if there's a problem communicating with the access API.
        """
        try:
            await self._access_client.revoke_upload_access(grant_id=grant_id)
        except AccessClientPort.GrantNotFoundError as err:
            raise self.GrantNotFoundError(grant_id=grant_id) from err

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
        grants = await self._access_client.get_upload_access_grants(
            user_id=user_id,
            iva_id=iva_id,
            box_id=box_id,
            valid=valid,
        )

        grants_with_info: list[GrantWithBoxInfo] = []
        for grant in grants:
            try:
                box = await self._box_dao.get_by_id(grant.box_id)
                grant_with_info = GrantWithBoxInfo(
                    **grant.model_dump(),
                    box_title=box.title,
                    box_description=box.description,
                    box_state=box.state,
                    box_version=box.version,
                )
                grants_with_info.append(grant_with_info)
            except ResourceNotFoundError:
                log.warning(
                    "Access grant %s has a box ID (%s) that doesn't exist in RS.",
                    grant.id,
                    grant.box_id,
                    extra={
                        "grant_id": grant.id,
                        "user_id": user_id,
                        "iva_id": iva_id,
                        "box_id": box_id,
                        "valid": valid,
                    },
                )
                continue

        # Sort grants for predictability
        return sorted(
            grants_with_info,
            key=lambda x: (
                -x.valid_until.timestamp(),  # DESC valid_until, rest is ASC
                x.user_id,
                x.iva_id,
                x.box_id,
                x.id,
            ),
        )

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
        # Verify access
        upload_box = await self.get_research_data_upload_box(
            box_id=box_id, auth_context=auth_context
        )

        # Get file list from file box service
        file_uploads = await self._file_upload_box_client.get_file_upload_list(
            box_id=upload_box.file_upload_box_id
        )

        # Get accessions from database
        file_ids = {f.id for f in file_uploads}
        accession_map = await self._file_controller.get_accessions_by_file_ids(
            file_ids=file_ids
        )
        for i, file_upload in enumerate(file_uploads):
            if file_upload.id in accession_map:
                file_uploads[i].accession = accession_map[file_upload.id]

        # Sort files by alias for predictability
        return sorted(file_uploads, key=lambda x: x.alias)

    async def upsert_file_upload_box(self, file_upload_box: FileUploadBox) -> None:
        """Handle FileUploadBox update events from file box service.

        Updates the corresponding ResearchDataUploadBox with latest file count and size.
        """
        try:
            research_data_upload_box = await self._box_dao.find_one(
                mapping={"file_upload_box_id": file_upload_box.id}
            )
            # Get the fields that matter (ID and storage alias don't change)
            new = {
                "file_upload_box_version": file_upload_box.version,
                "file_upload_box_state": file_upload_box.state,
                "file_count": file_upload_box.file_count,
                "size": file_upload_box.size,
                "max_size": file_upload_box.max_size,
                "storage_alias": file_upload_box.storage_alias,
            }
            updated_model = research_data_upload_box.model_copy(update=new)

            # Conditionally update data
            if updated_model.model_dump() != research_data_upload_box.model_dump():
                updated_model.version += 1
                await self._box_dao.update(updated_model)
        except NoHitsFoundError:
            # This might happen during initial creation - ignore
            log.info(
                "Did not find a matching ResearchDataUploadBox for inbound"
                + " FileUploadBox with ID %s. Was it just created?",
                file_upload_box.id,
            )

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
        # Check that the user has access to this box (if nonexistent, show unauthorized)
        is_ds = is_data_steward(auth_context)
        user_id = UUID(auth_context.id)
        has_access = (
            True
            if is_ds
            else (
                await self._access_client.check_box_access(
                    box_id=box_id, user_id=user_id
                )
            )
        )

        if not has_access:
            log.error(
                "User ID %s does not have access to ResearchDataUploadBox with"
                + " ID %s OR it does not exist.",
                user_id,
                box_id,
            )
            raise self.BoxAccessError("Unauthorized")

        # Return the box if it exists
        try:
            return await self._box_dao.get_by_id(box_id)
        except ResourceNotFoundError as err:
            raise self.BoxNotFoundError(box_id=box_id) from err

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
        if skip is not None and skip < 0:
            log.warning(
                "Received invalid arg %i for skip parameter, setting to None", skip
            )
            skip = None

        if limit is not None and limit < 0:
            log.warning(
                "Received invalid arg %i for limit parameter, setting to None", limit
            )
            limit = None

        # Check if user is a data steward
        is_ds = is_data_steward(auth_context)

        # Filter by state if specified
        mapping = {"state": state} if state is not None else {}

        if is_ds:
            # Data stewards can see all boxes
            boxes = [x async for x in self._box_dao.find_all(mapping=mapping)]
        else:
            # Regular users can only see boxes they have access to
            user_id = UUID(auth_context.id)
            accessible_box_ids = await self._access_client.get_accessible_upload_boxes(
                user_id=user_id
            )

            # Generally very few boxes per user, so make distinct call for each
            boxes = [
                await self._box_dao.get_by_id(box_id) for box_id in accessible_box_ids
            ]
            if state is not None:
                boxes = [x for x in boxes if x.state == state]

        count = len(boxes)
        boxes.sort(
            key=lambda x: (
                tuple(-ord(c) for c in x.state),  # Reverse alphabetical
                -x.last_changed.timestamp(),  # DESC by last_changed
                x.id,  # ASC by ID
            )
        )

        if skip:
            boxes = boxes[skip:]

        if limit:
            boxes = boxes[:limit]

        return BoxRetrievalResults(count=count, boxes=boxes)

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
            BoxLockedError: If the box is locked.
            OperationError: If there's a problem communicating with the file box service.
        """
        box = await self.get_research_data_upload_box(
            box_id=box_id, auth_context=auth_context
        )
        extra: dict[str, Any] = {"box_id": box_id, "file_id": file_id}

        if box.state == "locked":
            error = self.BoxLockedError()
            log.error(error, extra=extra)
            raise error

        try:
            await self._file_upload_box_client.delete_file_upload(
                box_id=box.file_upload_box_id, file_id=file_id
            )
        except FileBoxClientPort.FUBLockedError as err:
            error = self.BoxLockedError()
            log.error(error, extra=extra)
            raise error from err

    async def store_accession_map(
        self,
        *,
        box_id: UUID4,
        box_version: int,
        accession_map: dict[FileAccession, UUID4],
        study_id: PID,
    ) -> None:
        """Update the file accession map for a given box and publish an outbox event.
        This results in a version increment for the ResearchDataUploadBox.

        **Files with a state of *cancelled* or *failed* are ignored.**

        Check the specified ResearchDataUploadBox to verify it exists, that the version
        stated in the request is current, and that the box has not already been archived.

        Next, check the mapping to verify that every file ID is specified exactly
        once (and thus mapping is 1:1). This does not mean that the mapping contains
        all accessions in the study, just all the accessions associated with the upload
        box.

        Then retrieve the latest list of files in the box from the File Box API to
        verify that:
        - each file ID in the mapping exists in the retrieved list of files
        - all file IDs in the box are included in the mapping

        Finally, publish the mappings as events and update the RDUB version.

        Raises:
            BoxNotFoundError: If the box doesn't exist
            BoxVersionError: If the requested ResearchDataUploadBox version is outdated
            AccessionMapError: If
            - the box is already archived, or
            - the accession map includes a file ID that doesn't exist in the box, or
            - any files are specified more than once, or
            - any files in the box are left unmapped.
        """
        # Make sure the box exists
        try:
            box = await self._box_dao.get_by_id(box_id)
        except ResourceNotFoundError as err:
            raise self.BoxNotFoundError(box_id=box_id) from err

        # Make sure requested box version is current
        if box_version != box.version:
            log.error(
                "Accession Map update request specified version %i for RDUB %s, but"
                + " the current version is %i.",
                box_version,
                box_id,
                box.version,
            )
            raise self.BoxVersionError("Research Data Upload Box has changed.")

        # Don't allow changes to archived boxes
        if box.state == "archived":
            log.error(
                "Cannot update accessions for RDUB %s because it is already archived.",
                box_id,
                extra={"box_id": box_id},
            )
            raise self.AccessionMapError(
                "Data already archived - accessions cannot be modified.",
                error_type="archived",
            )

        # Make sure all file IDs are only specified once
        duplicate_file_ids = [
            str(file_id)
            for file_id, count in Counter(accession_map.values()).items()
            if count > 1
        ]
        if duplicate_file_ids:
            log.error(
                "Duplicate file IDs in accession map for box %s.",
                box_id,
                extra={
                    "rdub_id": box_id,
                    "fub_id": box.file_upload_box_id,
                    "duplicate_file_ids": duplicate_file_ids,
                },
            )
            raise self.AccessionMapError(
                f"Detected {len(duplicate_file_ids)} file ID(s) specified more than once.",
                error_type="duplicate_file_ids",
                affected_file_ids=duplicate_file_ids,
            )

        # Get files list from File Box API
        files = await self._file_upload_box_client.get_file_upload_list(
            box_id=box.file_upload_box_id
        )

        requested_file_ids = set(accession_map.values())

        # Make sure all specified file IDs are active uploads in the box
        file_ids_in_box = set(
            f.id for f in files if f.state not in ("cancelled", "failed")
        )
        if invalid_ids := (requested_file_ids - file_ids_in_box):
            log.error(
                "Accession map for box %s included unknown file IDs.",
                box_id,
                extra={
                    "rdub_id": box_id,
                    "fub_id": box.file_upload_box_id,
                    "unknown_file_ids": invalid_ids,
                },
            )
            raise self.AccessionMapError(
                "Invalid accession map. These file IDs are not in the box:"
                + f" {', '.join(map(str, invalid_ids))}.",
                error_type="unknown_file_ids",
                affected_file_ids=[str(fid) for fid in invalid_ids],
            )

        # Make sure all active files in the box are included in the mapping
        if unmapped_ids := (file_ids_in_box - requested_file_ids):
            log.error(
                "Accession map for box %s included unmapped file IDs.",
                box_id,
                extra={
                    "rdub_id": box_id,
                    "fub_id": box.file_upload_box_id,
                    "unmapped_file_ids": unmapped_ids,
                },
            )
            raise self.AccessionMapError(
                "Invalid accession map. These file IDs still need to be mapped:"
                f" {', '.join(map(str, unmapped_ids))}.",
                error_type="unmapped_file_ids",
                affected_file_ids=[str(fid) for fid in unmapped_ids],
            )

        # Submit the accession map via the file controller
        try:
            await self._file_controller.post_file_ids(
                study_id=study_id, file_id_map=accession_map
            )
        except FileControllerPort.ConflictingAccessionError as err:
            accessions = ", ".join(err.conflicting_accessions)
            raise self.AccessionMapError(
                f"The following accessions already have immutable mappings: {accessions}",
                error_type="accession_conflict",
                conflicting_accessions=err.conflicting_accessions,
            ) from err

        # Bump the RDUB version number
        updated_box = box.model_copy(update={"version": box.version + 1})
        await self._box_dao.update(updated_box)
