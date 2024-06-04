# Copyright 2021 - 2024 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

"""Main business-logic of this service"""

import contextlib
import logging
import re
import uuid
from datetime import timedelta

from ghga_service_commons.utils import utc_dates
from ghga_service_commons.utils.multinode_storage import (
    S3ObjectStorages,
    S3ObjectStoragesConfig,
)
from hexkit.protocols.objstorage import ObjectStorageProtocol
from pydantic import Field, PositiveInt, field_validator
from pydantic_settings import BaseSettings

from dcs.adapters.outbound.http import exceptions
from dcs.adapters.outbound.http.api_calls import (
    delete_secret_from_ekss,
    get_envelope_from_ekss,
)
from dcs.core import models
from dcs.ports.inbound.data_repository import DataRepositoryPort
from dcs.ports.outbound.dao import DrsObjectDaoPort, ResourceNotFoundError
from dcs.ports.outbound.event_pub import EventPublisherPort

log = logging.getLogger(__name__)


class DataRepositoryConfig(BaseSettings):
    """Config parameters needed for the DataRepository."""

    drs_server_uri: str = Field(
        ...,
        description="The base of the DRS URI to access DRS objects. Has to start with 'drs://'"
        + " and end with '/'.",
        examples=["drs://localhost:8080/"],
    )
    retry_access_after: int = Field(
        120,
        description="When trying to access a DRS object that is not yet in the outbox, instruct"
        + " to retry after this many seconds.",
    )
    ekss_base_url: str = Field(
        ...,
        description="URL containing host and port of the EKSS endpoint to retrieve"
        + " personalized envelope from",
        examples=["http://ekss:8080/"],
    )
    presigned_url_expires_after: PositiveInt = Field(
        ...,
        description="Expiration time in seconds for presigned URLS. Positive integer required",
        examples=[30],
    )
    cache_timeout: int = Field(
        7,
        description="Time in days since last access after which a file present in the "
        + "outbox should be unstaged and has to be requested from permanent storage again "
        + "for the next request.",
    )

    @field_validator("drs_server_uri")
    @classmethod
    def check_server_uri(cls, value: str):
        """Checks the drs_server_uri."""
        if not re.match(r"^drs://.+/$", value):
            message = (
                "The drs_server_uri has to start with 'drs://' and end with '/'"
                + f", got : {value}"
            )
            raise ValueError(message)

        return value


class DataRepository(DataRepositoryPort):
    """A service that manages a registry of DRS objects."""

    def __init__(
        self,
        *,
        config: DataRepositoryConfig,
        drs_object_dao: DrsObjectDaoPort,
        object_storages: S3ObjectStorages,
        event_publisher: EventPublisherPort,
    ):
        """Initialize with essential config params and outbound adapters."""
        self._config = config
        self._event_publisher = event_publisher
        self._drs_object_dao = drs_object_dao
        self._object_storages = object_storages

    def _get_drs_uri(self, *, drs_id: str) -> str:
        """Construct DRS URI for the given DRS ID."""
        return f"{self._config.drs_server_uri}{drs_id}"

    def _get_model_with_self_uri(
        self, *, drs_object: models.DrsObject
    ) -> models.DrsObjectWithUri:
        """Add the DRS self URI to an DRS object."""
        return models.DrsObjectWithUri(
            **drs_object.model_dump(),
            self_uri=self._get_drs_uri(drs_id=drs_object.file_id),
        )

    async def _get_access_model(
        self,
        *,
        drs_object: models.DrsObject,
        object_storage: ObjectStorageProtocol,
        bucket_id: str,
    ) -> models.DrsObjectWithAccess:
        """Get a DRS Object model with access information."""
        access_url = await object_storage.get_object_download_url(
            bucket_id=bucket_id,
            object_id=drs_object.object_id,
            expires_after=self._config.presigned_url_expires_after,
        )

        return models.DrsObjectWithAccess(
            **drs_object.model_dump(),
            self_uri=self._get_drs_uri(drs_id=drs_object.file_id),
            access_url=access_url,
        )

    async def access_drs_object(self, *, drs_id: str) -> models.DrsObjectResponseModel:
        """
        Serve the specified DRS object with access information.
        If it does not exists in the outbox, yet, a RetryAccessLaterError is raised that
        instructs to retry the call after a specified amount of time.
        """
        # make sure that metadata for the DRS object exists in the database:
        try:
            drs_object_with_access_time = await self._drs_object_dao.get_by_id(drs_id)
        except ResourceNotFoundError as error:
            drs_object_not_found = self.DrsObjectNotFoundError(drs_id=drs_id)
            log.error(drs_object_not_found)
            raise drs_object_not_found from error

        drs_object = models.DrsObject(
            **drs_object_with_access_time.model_dump(exclude={"last_accessed"})
        )

        drs_object_with_uri = self._get_model_with_self_uri(drs_object=drs_object)

        storage_alias = drs_object.s3_endpoint_alias

        try:
            bucket_id, object_storage = self._object_storages.for_alias(storage_alias)
        except KeyError as exc:
            storage_alias_not_configured = self.StorageAliasNotConfiguredError(
                alias=storage_alias
            )
            log.critical(storage_alias_not_configured)
            raise storage_alias_not_configured from exc

        # check if the file corresponding to the DRS object is already in the outbox:
        if not await object_storage.does_object_exist(
            bucket_id=bucket_id, object_id=drs_object.object_id
        ):
            log.info(f"File not in outbox for '{drs_id}'. Request staging...")
            # publish an event to request a stage of the corresponding file:
            await self._event_publisher.unstaged_download_requested(
                drs_object=drs_object_with_uri,
                target_bucket_id=bucket_id,
            )

            # instruct to retry later:
            raise self.RetryAccessLaterError(
                retry_after=self._config.retry_access_after
            )

        # Successfully staged, update access information now
        log.debug(f"Updating access time of for '{drs_id}'.")
        drs_object_with_access_time.last_accessed = utc_dates.now_as_utc()
        await self._drs_object_dao.update(drs_object_with_access_time)

        drs_object_with_access = await self._get_access_model(
            drs_object=drs_object,
            object_storage=object_storage,
            bucket_id=bucket_id,
        )

        # publish an event indicating the served download:
        await self._event_publisher.download_served(
            drs_object=drs_object_with_uri,
            target_bucket_id=bucket_id,
        )
        log.info(f"Sent download served event for '{drs_id}'.")

        # CLI needs to have the encrypted size to correctly download all file parts
        encrypted_size = await object_storage.get_object_size(
            bucket_id=bucket_id, object_id=drs_object.object_id
        )
        return drs_object_with_access.convert_to_drs_response_model(size=encrypted_size)

    async def cleanup_outbox_buckets(
        self, *, object_storages_config: S3ObjectStoragesConfig
    ):
        """Run cleanup task for all outbox buckets configured in the service config."""
        for storage_alias in object_storages_config.object_storages:
            await self.cleanup_outbox(storage_alias=storage_alias)

    async def cleanup_outbox(self, *, storage_alias: str):
        """
        Check if files present in the outbox have outlived their allocated time and remove
        all that do.
        For each file in the outbox, its 'last_accessed' field is checked and compared
        to the current datetime. If the threshold configured in the cache_timeout option
        is met or exceeded, the corresponding file is removed from the outbox.
        """
        # Run on demand through CLI, so crashing should be ok if the alias is not configured
        log.info(
            f"Starting outbox cleanup for storage identified by alias '{
                storage_alias}'."
        )
        try:
            bucket_id, object_storage = self._object_storages.for_alias(storage_alias)
        except KeyError as exc:
            storage_alias_not_configured = self.StorageAliasNotConfiguredError(
                alias=storage_alias
            )
            log.critical(storage_alias_not_configured)
            raise storage_alias_not_configured from exc

        threshold = utc_dates.now_as_utc() - timedelta(days=self._config.cache_timeout)

        # filter to get all files in outbox that should be removed
        object_ids = await object_storage.list_all_object_ids(bucket_id=bucket_id)
        log.debug(
            f"Retrieved list of deletion candidates for storage '{
                storage_alias}'"
        )

        for object_id in object_ids:
            try:
                drs_object = await self._drs_object_dao.find_one(
                    mapping={"object_id": object_id}
                )
            except ResourceNotFoundError as error:
                cleanup_error = self.CleanupError(object_id=object_id, from_error=error)
                log.critical(cleanup_error)
                raise cleanup_error from error

            # only remove file if last access is later than cache timeout days ago
            if drs_object.last_accessed <= threshold:
                log.info(
                    f"Deleting object '{object_id}' from storage '{
                        storage_alias}'."
                )
                try:
                    await object_storage.delete_object(
                        bucket_id=bucket_id, object_id=object_id
                    )
                except (
                    object_storage.ObjectError,
                    object_storage.ObjectStorageProtocolError,
                ) as error:
                    cleanup_error = self.CleanupError(
                        object_id=object_id, from_error=error
                    )
                    log.critical(cleanup_error)
                    raise cleanup_error from error

    async def register_new_file(self, *, file: models.DrsObjectBase):
        """Register a file as a new DRS Object."""
        object_id = str(uuid.uuid4())

        with contextlib.suppress(ResourceNotFoundError):
            await self._drs_object_dao.get_by_id(file.file_id)
            log.error(
                f"Could not register file with id '{
                    file.file_id}' as an entry already exists for this id."
            )
            return

        drs_object = models.DrsObject(**file.model_dump(), object_id=object_id)

        file_with_access_time = models.AccessTimeDrsObject(
            **drs_object.model_dump(),
            last_accessed=utc_dates.now_as_utc(),
        )
        # write file entry to database
        await self._drs_object_dao.insert(file_with_access_time)
        log.info(
            f"Successfully registered file with id '{
                file.file_id}' in the database."
        )

        # publish message that the drs file has been registered
        drs_object_with_uri = self._get_model_with_self_uri(drs_object=drs_object)
        await self._event_publisher.file_registered(drs_object=drs_object_with_uri)
        log.info(f"Sent successful registration event for file id '{
                 file.file_id}'.")

    async def serve_envelope(self, *, drs_id: str, public_key: str) -> str:
        """
        Retrieve envelope for the object with the given DRS ID

        :returns: base64 encoded envelope bytes
        """
        try:
            drs_object = await self._drs_object_dao.get_by_id(id_=drs_id)
        except ResourceNotFoundError as error:
            drs_object_not_found = self.DrsObjectNotFoundError(drs_id=drs_id)
            log.error(drs_object_not_found)
            raise drs_object_not_found from error

        log.info(f"Retrieving file envelope for DRS id '{drs_id}'.")
        try:
            envelope = get_envelope_from_ekss(
                secret_id=drs_object.decryption_secret_id,
                receiver_public_key=public_key,
                api_base=self._config.ekss_base_url,
            )
        except (
            exceptions.BadResponseCodeError,
            exceptions.RequestFailedError,
        ) as error:
            api_communication_error = self.APICommunicationError(
                api_url=self._config.ekss_base_url
            )
            log.error(api_communication_error)
            raise api_communication_error from error
        except exceptions.SecretNotFoundError as error:
            envelope_not_found = self.EnvelopeNotFoundError(
                object_id=drs_object.object_id
            )
            log.error(envelope_not_found)
            raise envelope_not_found from error

        return envelope

    async def delete_file(self, *, file_id: str) -> None:
        """Deletes a file from the outbox storage, the internal database and the
        corresponding secret from the secrets store.
        If no file or secret with that id exists, do nothing.

        Args:
            file_id: id for the file to delete.
        """
        # Get drs object from db
        try:
            drs_object = await self._drs_object_dao.get_by_id(id_=file_id)
        except ResourceNotFoundError:
            log.info(f"File with id '{file_id}' has already been deleted.")
            # If the db entry does not exist, we are done, as it is deleted last
            # and has already been deleted before
            return

        # call EKSS to remove file secret from vault
        with contextlib.suppress(exceptions.SecretNotFoundError):
            delete_secret_from_ekss(
                secret_id=drs_object.decryption_secret_id,
                api_base=self._config.ekss_base_url,
            )
            log.debug(f"Successfully deleted secret for '{
                      file_id}' from EKSS.")

        # At this point the alias is contained in the database and this is not a user
        # error, but a configuration issue. Is crashing the REST service ok here or do we
        # need a more graceful solution?
        alias = drs_object.s3_endpoint_alias
        try:
            bucket_id, object_storage = self._object_storages.for_alias(alias)
        except KeyError as exc:
            storage_alias_not_configured = self.StorageAliasNotConfiguredError(
                alias=alias
            )
            log.critical(storage_alias_not_configured)
            raise storage_alias_not_configured from exc

        # Try to remove file from S3
        with contextlib.suppress(object_storage.ObjectNotFoundError):
            await object_storage.delete_object(
                bucket_id=bucket_id, object_id=drs_object.object_id
            )
            log.debug(
                f"Successfully deleted file object for '{
                    file_id}' from object storage identified by '{alias}'."
            )

        # Remove file from database and send success event
        # Should not fail as we got the DRS object by the same ID
        await self._drs_object_dao.delete(id_=file_id)
        await self._event_publisher.file_deleted(file_id=file_id)
        log.info(f"Successfully deleted entries for file with id '{file_id}'.")
