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
#

"""Fixture for testing code that uses the S3ObjectStorage provider."""

from pytest import fixture

from fixtures.config import Config
from fixtures.http_client import HttpClient
from fixtures.state_manager import StateManager

__all__ = ["s3_fixture", "S3Fixture"]

DELETION_TIMEOUT = 60


class S3Fixture(StateManager):
    """Fixture for managing S3 resources"""

    def __init__(self, config: Config, http: HttpClient):
        self.config = config
        self.http = http

    config: Config

    def get_storage_config(self, storage_name: str):
        """Get the configuration for the given storage name.

        The storage name is used in test scenarios to refer to the
        configured storage node. The name might be different from the
        actual alias of the storage node. The test bed relies on two
        storage names: 'primary' and 'secondary'.
        """
        assert storage_name in [
            "primary",
            "secondary",
        ], f"Invalid storage name: {storage_name}"
        storage_config = getattr(self.config.object_storages, storage_name)
        assert storage_config, f"Storage config for storage '{storage_name}' not found"
        return storage_config

    def does_object_exist(
        self, bucket: str, object_id: str, storage_alias: str
    ) -> bool:
        """Check if an object exists in a bucket."""
        url = f"{self.config.sms_url}/objects/{storage_alias}/{bucket}/{object_id}"
        response = self.http.get(url, headers=self.auth_headers)
        return response.status_code == 200

    def empty_buckets(
        self,
        storage_aliases: str | list[str] | None = None,
        buckets: str | list[str] | None = None,
    ) -> None:
        """Empty the given bucket(s) in given storage alias(es)."""
        if buckets is None:
            buckets = [
                self.config.staging_bucket,
                self.config.permanent_bucket,
                self.config.outbox_bucket,
                self.config.inbox_bucket,
            ]

        if isinstance(buckets, str):
            buckets = [buckets]

        if storage_aliases is None:
            storage_aliases = [
                self.get_storage_config("primary").storage_alias,
                self.get_storage_config("secondary").storage_alias,
            ]

        if isinstance(storage_aliases, str):
            storage_aliases = [storage_aliases]

        for storage_alias in storage_aliases:
            for bucket_id in buckets:
                url = f"{self.config.sms_url}/objects/{storage_alias}/{bucket_id}"
                response = self.http.delete(
                    url, headers=self.auth_headers, timeout=DELETION_TIMEOUT
                )
                assert (
                    response.status_code == 204
                ), f"Failed to delete objects in {storage_alias}.{bucket_id}: {response.text}"


@fixture(name="s3", scope="session")
def s3_fixture(config: Config, http: HttpClient) -> S3Fixture:
    """Pytest fixture for tests depending on the S3ObjectStorage."""
    return S3Fixture(config=config, http=http)
