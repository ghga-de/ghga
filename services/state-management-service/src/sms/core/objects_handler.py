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
"""Contains classes that interface between inbound requests and object storage."""

from ghga_service_commons.utils.multinode_storage import S3ObjectStoragesConfig
from hexkit.protocols.objstorage import ObjectStorageProtocol
from hexkit.providers.s3 import S3ObjectStorage

from sms.config import Config
from sms.ports.inbound.objects_handler import ObjectsHandlerPort, S3ObjectStoragesPort


class S3ObjectStorages(S3ObjectStoragesPort):
    """S3-specific multi-node object storage instance.

    Provides access to object storage instances by alias on demand.
    This class is used instead of the one provided by ghga-service-commons because
    the bucket/config tuple returned by that version does not suit the needs of the SMS.
    """

    def __init__(self, *, config: S3ObjectStoragesConfig):
        """Use the `ghga-service-commons` config class to simplify configuration and
        not introduce a lot of variation.
        """
        self._config = config
        self._storages: dict[str, S3ObjectStorage] = {}

    def for_alias(self, endpoint_alias: str) -> S3ObjectStorage:
        """Return the object storage associated with the given alias.

        If the storage has not been accessed yet, it will be created and stored.

        Raises:
        - `AliasNotConfiguredError` if the alias does not exist in configuration.
        """
        # Validate the alias
        if endpoint_alias not in self._config.object_storages:
            raise self.AliasNotConfiguredError(alias=endpoint_alias)

        # Create the storage if it's not been created yet
        config = self._config.object_storages[endpoint_alias]
        if endpoint_alias not in self._storages:
            self._storages[endpoint_alias] = S3ObjectStorage(config=config.credentials)
        return self._storages[endpoint_alias]


class ObjectsHandler(ObjectsHandlerPort):
    """Class for multi-node (federated) object storage management."""

    def __init__(self, *, config: Config, object_storages: S3ObjectStoragesPort):
        self._config = config
        self._storages = object_storages

    async def does_object_exist(
        self, alias: str, bucket_id: str, object_id: str
    ) -> bool:
        """Check if an object exists in the specified bucket for the given alias.

        Returns `False` if the object is not in the bucket, otherwise `True`.

        Raises:
        - `AliasNotConfiguredError`: When the alias does not exist in configuration.
        - `BucketNotFoundError`: When the bucket does not exist.
        - `InvalidBucketIdError`: When the bucket ID is invalid.
        - `InvalidObjectIdError`: When the object ID is invalid.
        """
        storage = self._storages.for_alias(alias)

        try:
            # Checking object existence will not throw an error if the bucket does not
            # exist so we need to check that first
            if not await storage.does_bucket_exist(bucket_id=bucket_id):
                raise self.BucketNotFoundError(bucket_id=bucket_id)
        except ObjectStorageProtocol.BucketIdValidationError as err:
            raise self.InvalidBucketIdError(bucket_id=bucket_id) from err

        try:
            return await storage.does_object_exist(
                bucket_id=bucket_id, object_id=object_id
            )
        except ObjectStorageProtocol.ObjectIdValidationError as err:
            raise self.InvalidObjectIdError(object_id=object_id) from err
        except Exception as err:
            raise self.OperationError() from err

    async def empty_bucket(self, alias: str, bucket_id: str) -> None:
        """Delete all objects in the specified bucket for the given alias.

        Raises:
        - `AliasNotConfiguredError`: When the alias does not exist in configuration.
        - `InvalidBucketIdError`: When the bucket ID is invalid.
        - `ObjectNotFoundError`: When an object is unexpectedly absent.
        """
        storage = self._storages.for_alias(alias)

        # Get list of all objects in the bucket
        object_ids = await self.list_objects(alias=alias, bucket_id=bucket_id)

        # iterate and delete
        for object_id in object_ids:
            # State shouldn't change between list_objects() and here
            # if it does, something weird is going on and we should raise an error
            try:
                await storage.delete_object(bucket_id=bucket_id, object_id=object_id)
            except ObjectStorageProtocol.ObjectNotFoundError as err:
                raise self.ObjectNotFoundError(
                    object_id=object_id, bucket_id=bucket_id
                ) from err
            except Exception as err:
                raise self.OperationError() from err

    async def list_objects(self, alias: str, bucket_id: str) -> list[str]:
        """List all objects in the specified bucket for the given alias.

        Returns a list of object IDs contained by the bucket.

        Raises:
        - `AliasNotConfiguredError`: When the alias does not exist in configuration.
        - `BucketNotFoundError`: When the bucket does not exist.
        - `InvalidBucketIdError`: When the bucket ID is invalid.
        """
        storage = self._storages.for_alias(alias)

        try:
            return await storage.list_all_object_ids(bucket_id=bucket_id)
        except ObjectStorageProtocol.BucketNotFoundError as err:
            raise self.BucketNotFoundError(bucket_id=bucket_id) from err
        except ObjectStorageProtocol.BucketIdValidationError as err:
            raise self.InvalidBucketIdError(bucket_id=bucket_id) from err
        except Exception as err:
            raise self.OperationError() from err
