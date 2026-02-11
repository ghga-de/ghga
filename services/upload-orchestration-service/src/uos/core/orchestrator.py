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

"""Business logic service for the Upload Orchestration Service."""

import logging
from uuid import UUID

from ghga_service_commons.auth.ghga import AuthContext
from ghga_service_commons.utils.utc_dates import UTCDatetime
from hexkit.protocols.dao import DaoError, NoHitsFoundError, ResourceNotFoundError
from hexkit.utils import now_utc_ms_prec
from pydantic import UUID4

from uos.constants import VALID_STATE_TRANSITIONS
from uos.core.models import (
    AccessionMap,
    AccessionMapRequest,
    BoxRetrievalResults,
    FileUploadBox,
    FileUploadWithAccession,
    GrantWithBoxInfo,
    ResearchDataUploadBox,
    UpdateUploadBoxRequest,
    UploadBoxState,
)
from uos.ports.inbound.orchestrator import UploadOrchestratorPort
from uos.ports.outbound.audit import AuditRepositoryPort
from uos.ports.outbound.dao import AccessionMapDao, BoxDao
from uos.ports.outbound.http import AccessClientPort, FileBoxClientPort

log = logging.getLogger(__name__)

__all__ = ["UploadOrchestrator"]


def is_data_steward(auth_context: AuthContext) -> bool:
    """Returns a bool indicating if the auth context is for a Data Steward"""
    return "data_steward" in auth_context.roles


class UploadOrchestrator(UploadOrchestratorPort):
    """A class for orchestrating upload operations."""

    def __init__(
        self,
        *,
        box_dao: BoxDao,
        accession_map_dao: AccessionMapDao,
        audit_repository: AuditRepositoryPort,
        file_upload_box_client: FileBoxClientPort,
        access_client: AccessClientPort,
    ):
        self._box_dao = box_dao
        self._accession_map_dao = accession_map_dao
        self._audit_repository = audit_repository
        self._file_upload_box_client = file_upload_box_client
        self._access_client = access_client

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
        # Create FileUploadBox in external service
        file_upload_box_id = await self._file_upload_box_client.create_file_upload_box(
            storage_alias=storage_alias
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
        )

        # Store in repository & create audit record
        await self._box_dao.insert(box)
        await self._audit_repository.log_box_created(box=box, user_id=data_steward_id)
        return box.id

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
        # Get existing box if user has access to it
        box = await self.get_research_data_upload_box(
            box_id=box_id, auth_context=auth_context
        )

        # Make sure the request is not based on outdated info
        if box.version != request.version:
            log.error(
                "Can't update RDUB %s because the request is outdated.",
                box_id,
                extra={
                    "box_id": box_id,
                    "current_version": box.version,
                    "requested_version": request.version,
                },
            )
            raise self.VersionError(f"Research Data Upload Box {box_id} has changed")

        changed_fields = {
            k: v for k, v in request.model_dump().items() if v and getattr(box, k) != v
        }
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

        # If state is not changed, we can just update, emit audit log, and return
        if "state" not in changed_fields:
            await self._box_dao.update(updated_box)
            await self._audit_repository.log_box_updated(
                box=updated_box, user_id=user_id
            )
            return

        # Make sure the state change is valid, then update attributes and local DB copy
        self._check_state_change_is_valid(
            old_state=box.state, new_state=updated_box.state
        )
        updated_box.file_upload_box_state = updated_box.state
        updated_box.file_upload_box_version += 1
        await self._box_dao.update(updated_box)

        # Take the appropriate action for the state change and roll back if it fails
        try:
            await self._handle_state_change(old_box=box, updated_box=updated_box)
        except Exception:
            log.warning(
                "Failed to update FUB %s, rolling back changes for RDUB %s",
                box.file_upload_box_id,
                box_id,
            )
            await self._box_dao.update(box)
            raise
        else:
            await self._audit_repository.log_box_updated(
                box=updated_box, user_id=user_id
            )

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
        self, *, old_box: ResearchDataUploadBox, updated_box: ResearchDataUploadBox
    ) -> None:
        """Handle state change for a Research Data Upload Box and the corresponding
        FileUploadBox.
        """
        rdub_id = updated_box.id
        fub_id = updated_box.file_upload_box_id
        match (old_box.state, updated_box.state):
            case ("open", "locked"):  # lock the box
                await self._file_upload_box_client.lock_file_upload_box(box_id=fub_id)
            case ("locked", "open"):  # unlock the box
                await self._file_upload_box_client.unlock_file_upload_box(box_id=fub_id)
            case ("locked", "archived"):  # archive the box
                # Check prerequisites using old version number for logging purposes
                await self._check_archival_prerequisites(box=old_box)

                # Use old box data because `updated_box` has already been, well, updated
                try:
                    await self._file_upload_box_client.archive_file_upload_box(
                        box_id=fub_id, version=old_box.file_upload_box_version
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
                    raise self.VersionError(
                        f"File Upload Box {fub_id} version is out of date."
                    ) from version_err
            case _:
                # maybe we allowed a new state change but forgot to handle it here?
                raise NotImplementedError()

    async def _check_archival_prerequisites(
        self, *, box: ResearchDataUploadBox
    ) -> None:
        """Archive a research data upload box.

        Raises:
            ArchivalPrereqsError: If there are any files in the box that don't yet have
                an accession assigned OR if the box is still in the 'open' state.
            OperationError: If there's a problem querying the file box service.
        """
        box_id = box.id

        try:
            db_map = await self._accession_map_dao.get_by_id(box_id)
        except ResourceNotFoundError as err:
            log.error(
                "Can't archive RDUB %s because no accession map could be found.",
                box_id,
                extra={"box_id": box_id, "version": box.version},
            )
            raise self.ArchivalPrereqsError(
                "Accessions have not been assigned"
            ) from err

        # Get files list from File Box API - this always gets the latest data
        files = await self._file_upload_box_client.get_file_upload_list(
            box_id=box.file_upload_box_id
        )

        # Make sure all files have an accession number
        file_ids_in_box = set(f.id for f in files)
        file_ids_in_map = set(db_map.mapping.values())
        unassigned_files = file_ids_in_box - file_ids_in_map

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
        # TODO: Should we block access to archived boxes, or let that be handled IRL?
        # Verify the upload box exists
        await self._box_dao.get_by_id(box_id)

        # Grant access via Claims Repository Service (errors handled by access client)
        await self._access_client.grant_upload_access(
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
                )
                grants_with_info.append(grant_with_info)
            except ResourceNotFoundError:
                log.warning(
                    "Access grant %s has a box ID (%s) that doesn't exist in UOS.",
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
            box_id=upload_box.file_upload_box_id,
        )

        # Get accessions from database
        try:
            accessions = await self._accession_map_dao.get_by_id(box_id)
        except ResourceNotFoundError:
            log.warning("No accession map found for box ID %s", box_id)
        else:
            # Invert the dictionary so we can look up accession by file ID
            acc_dict = {v: k for k, v in accessions.mapping.items()}
            for i in range(len(file_uploads)):
                file_id = file_uploads[i].id
                if file_id in acc_dict:
                    file_uploads[i].accession = acc_dict.get(file_id)

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
        # Make sure the box exists
        try:
            box = await self._box_dao.get_by_id(box_id)
        except ResourceNotFoundError as err:
            raise self.BoxNotFoundError(box_id=box_id) from err

        # Make sure requested box version is current
        if request.version != box.version:
            log.error(
                "Accession Map update request specified version %i for RDUB %s, but"
                + " the current version is %i.",
                request.version,
                box_id,
                box.version,
            )
            raise self.VersionError("Research Data Upload Box has changed.")

        # Don't allow changes to archived boxes
        if box.state == "archived":
            log.error(
                "Cannot update accessions for RDUB %s because it is already archived.",
                box_id,
                extra={"box_id": box_id},
            )
            raise self.AccessionMapError(
                "Data already archived - accessions cannot be modified."
            )

        # Make sure all file IDs are only specified once
        unique_file_ids = set(request.mapping.values())
        if dupe_count := (len(request.mapping) - len(unique_file_ids)):
            log.error(
                "Duplicate file IDs in accession map for box %s.",
                box_id,
                extra={
                    "rdub_id": box_id,
                    "fub_id": box.file_upload_box_id,
                    "duplicate_count": dupe_count,
                },
            )
            raise self.AccessionMapError(
                f"Detected {dupe_count} file ID(s) specified more than once."
            )

        # Get files list from File Box API
        files = await self._file_upload_box_client.get_file_upload_list(
            box_id=box.file_upload_box_id
        )

        # Make sure all specified file IDs are active uploads in the box
        file_ids_in_box = set(
            f.id for f in files if f.state not in ("cancelled", "failed")
        )
        if invalid_ids := (unique_file_ids - file_ids_in_box):
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
                + f" {', '.join(map(str, invalid_ids))}."
            )

        # Make sure all active files in the box are included in the mapping
        if unmapped_ids := (file_ids_in_box - unique_file_ids):
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
                f" {', '.join(map(str, unmapped_ids))}."
            )

        try:
            # Store the data and publish an outbox event
            accession_mapping = AccessionMap(box_id=box_id, mapping=request.mapping)
            await self._accession_map_dao.upsert(accession_mapping)
            log.info("Accession map upserted for RDUB %s", box_id)
        except DaoError as err:
            log.error(
                "Unexpected database error prevented accession map upsert for box %s",
                box_id,
                exc_info=True,
                extra={
                    "rdub_id": box_id,
                    "rdub_version": box.version,
                    "fub_id": box.file_upload_box_id,
                },
            )
            raise self.AccessionMapError("Failed to update accession map.") from err
        else:
            # Bump the RDUB version number
            updated_box = box.model_copy(update={"version": box.version + 1})
            await self._box_dao.update(updated_box)
