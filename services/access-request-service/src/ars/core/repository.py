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
#

"""A repository for access requests."""

import logging
from datetime import timedelta
from operator import attrgetter
from typing import Any, cast

from ghga_service_commons.auth.ghga import AuthContext, has_role
from ghga_service_commons.utils.utc_dates import now_as_utc
from pydantic import Field
from pydantic_settings import BaseSettings

from ars.core.models import (
    AccessRequest,
    AccessRequestCreationData,
    AccessRequestStatus,
    Dataset,
)
from ars.core.roles import DATA_STEWARD_ROLE
from ars.ports.inbound.repository import AccessRequestRepositoryPort
from ars.ports.outbound.access_grants import AccessGrantsPort
from ars.ports.outbound.daos import (
    AccessRequestDaoPort,
    DatasetDaoPort,
    ResourceNotFoundError,
)
from ars.ports.outbound.event_pub import EventPublisherPort

__all__ = ["AccessRequestConfig", "AccessRequestRepository"]

log = logging.getLogger(__name__)


class AccessRequestConfig(BaseSettings):
    """Config parameters needed for the AccessRequestRepository."""

    access_upfront_max_days: int = Field(
        default=6 * 30,
        description="The maximum lead time in days to request access grants",
    )
    access_grant_min_days: int = Field(
        default=7,
        description="The minimum number of days that the access will be granted",
    )
    access_grant_max_days: int = Field(
        default=2 * 365,
        description="The maximum number of days that the access can be granted",
    )


class AccessRequestRepository(AccessRequestRepositoryPort):
    """A repository for access requests."""

    def __init__(
        self,
        *,
        config: AccessRequestConfig,
        access_request_dao: AccessRequestDaoPort,
        dataset_dao: DatasetDaoPort,
        event_publisher: EventPublisherPort,
        access_grants: AccessGrantsPort,
    ):
        """Initialize with specific configuration and outbound adapter."""
        self._max_lead_time = timedelta(days=config.access_upfront_max_days)
        self._min_duration = timedelta(days=config.access_grant_min_days)
        self._max_duration = timedelta(days=config.access_grant_max_days)
        self._request_dao = access_request_dao
        self._dataset_dao = dataset_dao
        self._event_publisher = event_publisher
        self._access_grants = access_grants

    async def create(
        self, creation_data: AccessRequestCreationData, *, auth_context: AuthContext
    ) -> AccessRequest:
        """Create an access request and store it in the repository.

        Returns the created access request object.

        Users may only create access requests for themselves.

        Raises:
        - `AccessRequestAuthorizationError` if the user is not authorized.
        - `AccessRequestInvalidDuration` error if the dates are invalid.
        """
        user_id = auth_context.id
        if not user_id or creation_data.user_id != user_id:
            authorization_error = self.AccessRequestAuthorizationError("Not authorized")
            log.error(authorization_error)
            raise authorization_error

        request_created = now_as_utc()

        access_starts = creation_data.access_starts
        if request_created > access_starts:
            # force the start to be not earlier than the request creation date
            access_starts = request_created
            creation_data = creation_data.model_copy(
                update={"access_starts": access_starts}
            )
        if access_starts > request_created + self._max_lead_time:
            invalid_duration_error = self.AccessRequestInvalidDuration(
                "Access start date is invalid"
            )
            log.error(invalid_duration_error)
            raise invalid_duration_error
        access_ends = creation_data.access_ends
        if not self._min_duration <= access_ends - access_starts <= self._max_duration:
            invalid_duration_error = self.AccessRequestInvalidDuration(
                "Access end date is invalid"
            )
            log.error(invalid_duration_error)
            raise invalid_duration_error

        full_user_name = auth_context.name
        if auth_context.title:
            full_user_name = auth_context.title + " " + full_user_name

        access_request = AccessRequest(
            **creation_data.model_dump(),
            full_user_name=full_user_name,
            request_created=request_created,
        )

        await self._request_dao.insert(access_request)

        await self._event_publisher.publish_request_created(request=access_request)

        return access_request

    async def get(
        self,
        *,
        dataset_id: str | None = None,
        user_id: str | None = None,
        status: AccessRequestStatus | None = None,
        auth_context: AuthContext,
    ) -> list[AccessRequest]:
        """Get the list of all access requests with the given properties.

        Only data stewards may list requests created by other users.

        Raises an `AccessRequestAuthorizationError` if the user is not authorized.
        """
        if not auth_context.id:
            authorization_error = self.AccessRequestAuthorizationError("Not authorized")
            log.error(authorization_error)
            raise authorization_error
        is_data_steward = has_role(auth_context, DATA_STEWARD_ROLE)
        if not is_data_steward:
            if user_id is None:
                user_id = auth_context.id
            elif user_id != auth_context.id:
                authorization_error = self.AccessRequestAuthorizationError(
                    "Not authorized"
                )
                log.error(authorization_error)
                raise authorization_error

        mapping: dict[str, Any] = {}
        if user_id is not None:
            mapping["user_id"] = user_id
        if dataset_id is not None:
            mapping["dataset_id"] = dataset_id
        if status is not None:
            mapping["status"] = status

        requests = [
            request async for request in self._request_dao.find_all(mapping=mapping)
        ]

        # latests requests should be served first
        requests.sort(key=attrgetter("request_created"), reverse=True)

        if not is_data_steward:
            requests = list(map(self._hide_internals, requests))

        return requests

    async def update(  # noqa: C901
        self,
        access_request_id: str,
        *,
        status: AccessRequestStatus,
        auth_context: AuthContext,
        iva_id: str | None = None,
    ) -> None:
        """Update the status of the access request.

        If the status is set to allowed, an IVA ID must be provided or already exist.

        Only data stewards may use this method.

        Raises:
        - `AccessRequestAuthorizationError` if the user is not authorized.
        - `AccessRequestNotFoundError` if the specified request was not found.
        - `AccessRequestMissingIva` if an IVA is needed but not provided.
        - `AccessRequestInvalidState` error if the specified state is invalid.
        - `AccessRequestServerError` if the grant could not be registered.
        """
        user_id = auth_context.id
        if not user_id or not has_role(auth_context, DATA_STEWARD_ROLE):
            authorization_error = self.AccessRequestAuthorizationError("Not authorized")
            log.error(authorization_error)
            raise authorization_error

        try:
            request = await self._request_dao.get_by_id(access_request_id)
        except ResourceNotFoundError as error:
            not_found_error = self.AccessRequestNotFoundError(
                "Access request not found"
            )
            log.error(not_found_error, extra={"access_request_id": access_request_id})
            raise not_found_error from error
        if request.status == status:
            invalid_state_error = self.AccessRequestInvalidState(
                "Same status is already set"
            )
            log.error(invalid_state_error)
            raise invalid_state_error
        if request.status != AccessRequestStatus.PENDING:
            invalid_state_error = self.AccessRequestInvalidState(
                "Status cannot be reverted"
            )
            log.error(invalid_state_error)
            raise invalid_state_error
        if not iva_id:
            iva_id = request.iva_id
        if status == AccessRequestStatus.ALLOWED and not iva_id:
            missing_iva_error = self.AccessRequestMissingIva(
                "An IVA ID must be specified"
            )
            log.error(missing_iva_error)
            raise missing_iva_error

        modified_request = request.model_copy(
            update={
                "iva_id": iva_id,
                "status": status,
                "status_changed": now_as_utc(),
                "changed_by": user_id,
            }
        )

        await self._request_dao.update(modified_request)

        if status == AccessRequestStatus.ALLOWED:
            # Try to register as download access grant
            try:
                await self._access_grants.grant_download_access(
                    user_id=request.user_id,
                    iva_id=cast(str, iva_id),  # has already been checked above
                    dataset_id=request.dataset_id,
                    valid_from=request.access_starts,
                    valid_until=request.access_ends,
                )
            except self._access_grants.AccessGrantsError as error:
                # roll back the status update
                await self._request_dao.update(request)
                server_error = self.AccessRequestServerError(
                    f"Could not register the download access grant: {error}"
                )
                log.error(server_error)
                raise server_error from error

        # Emit events that communicate the fate of the access request
        if status == AccessRequestStatus.DENIED:
            await self._event_publisher.publish_request_denied(request=request)
        elif status == AccessRequestStatus.ALLOWED:
            await self._event_publisher.publish_request_allowed(request=request)

    @staticmethod
    def _hide_internals(request: AccessRequest) -> AccessRequest:
        """Blank out internal information in the request"""
        return request.model_copy(update={"changed_by": None})

    async def register_dataset(self, dataset: Dataset) -> None:
        """Register a dataset in the repository."""
        await self._dataset_dao.upsert(dataset)

    async def delete_dataset(self, dataset_id: str) -> None:
        """Remove the dataset with the given ID.

        Raises a `DatasetNotFoundError` if the dataset was not found.
        """
        try:
            return await self._dataset_dao.delete(id_=dataset_id)
        except ResourceNotFoundError as error:
            dataset_not_found_error = self.DatasetNotFoundError("Dataset not found")
            log.error(dataset_not_found_error, extra={"dataset_id": dataset_id})
            raise dataset_not_found_error from error

    async def get_dataset(self, dataset_id: str) -> Dataset:
        """Get the dataset with the given ID.

        Raises a `DatasetNotFoundError` if the dataset was not found.
        """
        try:
            return await self._dataset_dao.get_by_id(dataset_id)
        except ResourceNotFoundError as error:
            dataset_not_found_error = self.DatasetNotFoundError("Dataset not found")
            log.error(dataset_not_found_error, extra={"dataset_id": dataset_id})
            raise dataset_not_found_error from error
