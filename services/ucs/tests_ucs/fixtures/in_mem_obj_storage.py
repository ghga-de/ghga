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

"""Mock object storage class"""

from ghga_service_commons.utils.multinode_storage import (
    ObjectStorages,
    S3ObjectStoragesConfig,
)
from hexkit.providers.s3 import S3ObjectStorage


class InMemS3ObjectStorages(ObjectStorages):
    """S3 specific multi node object storage instance.

    Object storage instances for a given alias should be instantiated lazily on demand.
    """

    def __init__(self, *, config: S3ObjectStoragesConfig):
        self._config = config
        self._data: dict[str, S3ObjectStorage] = {}

    def for_alias(self, endpoint_alias: str) -> tuple[str, S3ObjectStorage]:
        """Get bucket ID and object storage instance for a specific alias."""
        node_config = self._config.object_storages[endpoint_alias]
        try:
            return node_config.bucket, self._data[node_config.bucket]
        except KeyError:
            self._data[node_config.bucket] = S3ObjectStorage(
                config=node_config.credentials
            )
            return node_config.bucket, self._data[node_config.bucket]
