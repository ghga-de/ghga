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

"""Test the multi node object storage utilities."""

from unittest.mock import patch

import pytest
from pydantic import SecretStr

from ghga_service_commons.utils.multinode_storage import (
    S3ObjectStorageNodeConfig,
    S3ObjectStorages,
    S3ObjectStoragesConfig,
)
from hexkit.providers.s3 import S3Config


def _make_config() -> S3ObjectStoragesConfig:
    """Build a config with two distinct object storage nodes."""

    def _node(bucket: str) -> S3ObjectStorageNodeConfig:
        return S3ObjectStorageNodeConfig(
            bucket=bucket,
            credentials=S3Config(
                s3_endpoint_url=f"http://localhost/{bucket}",
                s3_access_key_id="test-key",
                s3_secret_access_key=SecretStr("test-secret"),
            ),
        )

    return S3ObjectStoragesConfig(
        object_storages={"node1": _node("bucket1"), "node2": _node("bucket2")}
    )


def test_for_alias_uses_cache_on_subsequent_calls():
    """Ensure subsequent calls to for_alias for the same alias reuse the cached instance."""
    storages = S3ObjectStorages(config=_make_config())

    with patch(
        "ghga_service_commons.utils.multinode_storage.S3ObjectStorage"
    ) as storage_cls:
        bucket, storage = storages.for_alias("node1")
        second_bucket, second_storage = storages.for_alias("node1")

    # The storage instance is only constructed once, then served from the cache.
    storage_cls.assert_called_once()
    assert storage is second_storage
    assert storage is storage_cls.return_value

    # The bucket ID is returned consistently for both calls.
    assert bucket == second_bucket == "bucket1"


def test_for_alias_caches_per_alias():
    """Ensure distinct aliases are cached independently and yield distinct instances."""
    storages = S3ObjectStorages(config=_make_config())

    with patch(
        "ghga_service_commons.utils.multinode_storage.S3ObjectStorage",
        side_effect=lambda **_: object(),
    ) as storage_cls:
        _, storage_node1 = storages.for_alias("node1")
        _, storage_node2 = storages.for_alias("node2")
        # Re-requesting each alias still hits the cache rather than reconstructing.
        _, storage_node1_again = storages.for_alias("node1")
        _, storage_node2_again = storages.for_alias("node2")

    # One construction per distinct alias, none for the repeated requests.
    assert storage_cls.call_count == 2
    assert storage_node1 is storage_node1_again
    assert storage_node2 is storage_node2_again
    assert storage_node1 is not storage_node2


def test_for_alias_unknown_alias_raises():
    """Ensure an unknown alias raises KeyError and does not populate the cache."""
    storages = S3ObjectStorages(config=_make_config())

    with patch("ghga_service_commons.utils.multinode_storage.S3ObjectStorage"):
        with pytest.raises(KeyError):
            storages.for_alias("does-not-exist")
    assert len(storages._storage_cache) == 0
