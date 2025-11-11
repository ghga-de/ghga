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

"""Business logic service for the Upload Orchestration Service."""

import logging
from uuid import UUID

from ghga_event_schemas.pydantic_ import (
    FileUpload,
    FileUploadBox,
    ResearchDataUploadBox,
    ResearchDataUploadBoxState,
)
from ghga_service_commons.auth.ghga import AuthContext
from ghga_service_commons.utils.utc_dates import UTCDatetime
from hexkit.protocols.dao import NoHitsFoundError, ResourceNotFoundError
from hexkit.utils import now_utc_ms_prec
from pydantic import UUID4

from uos.core.models import (
    BoxRetrievalResults,
    GrantWithBoxInfo,
    UpdateUploadBoxRequest,
)
from uos.ports.inbound.orchestrator import UploadOrchestratorPort
from uos.ports.outbound.audit import AuditRepositoryPort
from uos.ports.outbound.dao import BoxDao
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
        audit_repository: AuditRepositoryPort,
        file_upload_box_client: FileBoxClientPort,
        access_client: AccessClientPort,
    ):
        self._box_dao = box_dao
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
            OperationError: if there's a problem creating a corresponding FileUploadBox.
        """
        # Create FileUploadBox in external service
        file_upload_box_id = await self._file_upload_box_client.create_file_upload_box(
            storage_alias=storage_alias
        )

        # Create ResearchDataUploadBox
        box = ResearchDataUploadBox(
            state=ResearchDataUploadBoxState.OPEN,
            title=title,
            description=description,
            last_changed=now_utc_ms_prec(),
            changed_by=data_steward_id,
            file_upload_box_id=file_upload_box_id,
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
            OperationError: if there's a problem updating the corresponding FileUploadBox.
        """
        # Get existing box if user has access to it
        box = await self.get_research_data_upload_box(
            box_id=box_id, auth_context=auth_context
        )
        changed_fields = {
            k: v for k, v in request.model_dump().items() if v and getattr(box, k) != v
        }
        updated_box = box.model_copy(update=changed_fields)

        # If not a data steward, the only acceptable update is to move from OPEN to LOCKED
        is_ds = is_data_steward(auth_context)
        if not is_ds and not (
            changed_fields == {"state": "locked"}
            and box.state == ResearchDataUploadBoxState.OPEN
        ):
            raise self.BoxAccessError("Unauthorized")

        # If locking or unlocking, communicate with service that owns file upload boxes
        #  (errors handled in file_upload_box_client)
        if (
            updated_box.state
            and updated_box.state != box.state
            and box.state == ResearchDataUploadBoxState.OPEN
        ):
            await self._file_upload_box_client.lock_file_upload_box(
                box_id=box.file_upload_box_id
            )
            updated_box.locked = True
        elif (
            updated_box.state
            and updated_box.state == ResearchDataUploadBoxState.OPEN
            and updated_box.state != box.state
        ):
            await self._file_upload_box_client.unlock_file_upload_box(
                box_id=box.file_upload_box_id
            )
            updated_box.locked = False

        # Update the research data upload box in the DB
        updated_box.last_changed = now_utc_ms_prec()
        user_id = UUID(auth_context.id)
        updated_box.changed_by = user_id
        await self._box_dao.update(updated_box)

        # Create audit record
        await self._audit_repository.log_box_updated(box=updated_box, user_id=user_id)

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
            AccessAPIError: if there's a problem communicating with the access API.
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
    ) -> list[FileUpload]:
        """Get list of file uploads for a research data upload box.

        Returns a list of file uploads in the upload box

        Raises:
            BoxNotFoundError: If the box doesn't exist.
            BoxAccessError: If the user doesn't have access to the box.
            OperationError: if there's a problem querying the file box service.
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
                "locked": file_upload_box.locked,
                "file_count": file_upload_box.file_count,
                "size": file_upload_box.size,
            }
            updated_model = research_data_upload_box.model_copy(update=new)

            # Conditionally update data
            if updated_model.model_dump() != research_data_upload_box.model_dump():
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
        locked: bool | None = None,
    ) -> BoxRetrievalResults:
        """Retrieve all Research Data Upload Boxes, optionally paginated.

        For data stewards, returns all boxes. For regular users, only returns boxes
        they have access to according to the Access API.

        Results are sorted first by locked status (unlocked first), then by most
        recently changed, and then by box ID.

        Returns a BoxRetrievalResults instance with the boxes and unpaginated count.
        """
        if skip is not None and skip < 0:
            skip = None
            log.warning("Received invalid arg %i for skip parameter, setting to 0")

        if limit is not None and limit < 0:
            limit = None
            log.warning("Received invalid arg %i for limit parameter, setting to None")

        # Check if user is a data steward
        is_ds = is_data_steward(auth_context)

        # Filter by locked status if specified
        mapping = {"locked": locked} if locked is not None else {}

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
            if locked is not None:
                boxes = [x for x in boxes if x.locked == locked]

        count = len(boxes)
        boxes.sort(
            key=lambda x: (
                x.locked,  # sort so unlocked are first, locked last (False < True)
                -x.last_changed.timestamp(),  # DESC by last_changed
                x.id,  # ASC by ID
            )
        )

        if skip:
            boxes = boxes[skip:]

        if limit:
            boxes = boxes[:limit]

        return BoxRetrievalResults(count=count, boxes=boxes)
