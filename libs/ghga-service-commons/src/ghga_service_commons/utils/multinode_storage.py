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
#
"""Configuration for multiple object storage nodes"""

from abc import ABC, abstractmethod

from pydantic_settings import BaseSettings

from hexkit.protocols.objstorage import ObjectStorageProtocol
from hexkit.providers.s3 import S3Config, S3ObjectStorage

__all__ = [
    "ObjectStorages",
    "S3ObjectStorageNodeConfig",
    "S3ObjectStorages",
    "S3ObjectStoragesConfig",
]


class S3ObjectStorageNodeConfig(BaseSettings):
    """Configuration for one specific object storage node and one bucket in it.

    The bucket is the main bucket that the service is responsible for.
    """

    bucket: str
    credentials: S3Config


class S3ObjectStoragesConfig(BaseSettings):
    """Configuration for all available object storage nodes indexed by location label.

    The location label serves as an alias to access different object storage instances.
    """

    object_storages: dict[str, S3ObjectStorageNodeConfig]


class ObjectStorages(ABC):
    """Protocol for a multi node object storage instance.

    Object storage instances for a given alias should be instantiated lazily on demand.
    """

    @abstractmethod
    def for_alias(self, endpoint_alias: str) -> tuple[str, ObjectStorageProtocol]:
        """Get bucket ID and object storage instance for a specific alias."""


class S3ObjectStorages(ObjectStorages):
    """S3 specific multi node object storage instance.

    Object storage instances for a given alias should be instantiated lazily on demand.
    """

    def __init__(self, *, config: S3ObjectStoragesConfig):
        self._config = config
        self._storage_cache: dict[str, S3ObjectStorage] = {}

    def for_alias(self, endpoint_alias: str) -> tuple[str, S3ObjectStorage]:
        """Get bucket ID and object storage instance for a specific alias.

        The object storage instance is created lazily on first access and cached,
        so subsequent calls for the same alias reuse the same instance.

        Caveat: Its underlying boto3 client is thread-safe, but any boto3 resource used is not.
        This is not an issue in the current hexkit implementation, but might change if more
        resource usage is introduced.
        """
        node_config = self._config.object_storages[endpoint_alias]
        storage = self._storage_cache.get(endpoint_alias)
        if storage is None:
            storage = S3ObjectStorage(config=node_config.credentials)
            self._storage_cache[endpoint_alias] = storage
        return node_config.bucket, storage
