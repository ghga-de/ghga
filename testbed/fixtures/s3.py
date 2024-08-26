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


class S3Fixture(StateManager):
    """Fixture for managing S3 resources"""

    def __init__(self, config: Config, http: HttpClient):
        self.config = config
        self.http = http

    config: Config

    def does_object_exist(
        self,
        bucket: str,
        object_id: str,
        storage_alias: str | None = None,
    ) -> bool:
        """Check if an object exists in a bucket."""
        storage_alias = (
            storage_alias or "test"
        )  # Hardcoded value will be fixed in file federation implementation
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

        storage_aliases = storage_aliases or [
            "test"
        ]  # Hardcoded value will be fixed in file federation implementation

        if isinstance(storage_aliases, str):
            storage_aliases = [storage_aliases]

        for storage_alias in storage_aliases:
            for bucket_id in buckets:
                url = f"{self.config.sms_url}/objects/{storage_alias}/{bucket_id}"
                response = self.http.delete(url, headers=self.auth_headers)
                assert (
                    response.status_code == 204
                ), f"Failed to delete objects in {storage_alias}.{bucket_id}: {response.text}"


@fixture(name="s3", scope="session")
def s3_fixture(config: Config, http: HttpClient) -> S3Fixture:
    """Pytest fixture for tests depending on the S3ObjectStorage."""
    return S3Fixture(config=config, http=http)
