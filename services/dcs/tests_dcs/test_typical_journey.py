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

"""Tests typical user journeys"""

import logging
import re
from datetime import timedelta
from uuid import uuid4

import httpx
import pytest
from fastapi import status
from hexkit.providers.akafka.testutils import ExpectedEvent
from hexkit.providers.s3.testutils import FileObject, temp_file_object
from hexkit.utils import now_utc_ms_prec
from pytest_httpx import HTTPXMock, httpx_mock  # noqa: F401

from dcs.core import models
from dcs.core.errors import StorageAliasNotConfiguredError
from dcs.core.models import FileDownloadServed, NonStagedFileRequested
from tests_dcs.fixtures.joint import (
    CleanupFixture,
    PopulatedFixture,
)
from tests_dcs.fixtures.mock_api.app import router
from tests_dcs.fixtures.utils import generate_work_order_token

unintercepted_hosts: list[str] = ["localhost", "docker"]

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.httpx_mock(
        should_mock=lambda request: request.url.path.startswith("/ekss"),
    ),
]


async def test_happy_journey(
    populated_fixture: PopulatedFixture,
    tmp_file: FileObject,
    httpx_mock: HTTPXMock,  # noqa: F811
):
    """Simulates a typical, successful API journey."""
    joint_fixture = populated_fixture.joint_fixture

    # explicitly handle ekss API calls (and name unintercepted hosts above)
    httpx_mock.add_callback(
        callback=router.handle_request,
        url=re.compile(rf"^{joint_fixture.config.ekss_base_url}.*"),
    )

    example_file = populated_fixture.example_file
    endpoint_alias = joint_fixture.endpoint_aliases.valid_node
    s3 = joint_fixture.s3

    drs_object = await populated_fixture.mongodb_dao.get_by_id(example_file.file_id)
    object_id = drs_object.object_id

    # generate work order token
    accession = "GHGA001"
    work_order_token = generate_work_order_token(
        file_id=example_file.file_id,
        accession=accession,
        jwk=joint_fixture.jwk,
        valid_seconds=120,
    )

    # modify default headers:
    joint_fixture.rest_client.headers = httpx.Headers(
        {"Authorization": f"Bearer {work_order_token}"}
    )

    # request access to the newly registered file:
    # (An check that an event is published indicating that the file is not in
    # download bucket yet.)

    non_staged_requested_event = NonStagedFileRequested(
        file_id=example_file.file_id,
        storage_alias=endpoint_alias,
        target_bucket_id=joint_fixture.bucket_id,
        target_object_id=object_id,
        decrypted_sha256=example_file.decrypted_sha256,
    )
    async with joint_fixture.kafka.expect_events(
        events=[
            ExpectedEvent(
                payload=non_staged_requested_event.model_dump(mode="json"),
                type_=joint_fixture.config.files_to_stage_type,
            )
        ],
        in_topic=joint_fixture.config.files_to_stage_topic,
    ):
        response = await joint_fixture.rest_client.get(
            f"/objects/{accession}", timeout=5
        )
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert "Cache-Control" in response.headers
    assert response.headers["Cache-Control"] == "no-store"
    retry_after = int(response.headers["Retry-After"])
    # the example file is small, so we expect the minimum wait time
    assert retry_after == joint_fixture.config.retry_after_min

    # place the requested file into the download bucket (it is not important here that
    # the file content does not match the announced decrypted_sha256 checksum):
    file_object = tmp_file.model_copy(
        update={
            "bucket_id": joint_fixture.bucket_id,
            "object_id": str(object_id),
        }
    )

    await s3.populate_file_objects([file_object])

    # retry the access request:
    # (And check that an event is published indicating that a download was served.)
    download_served_event = FileDownloadServed(
        file_id=example_file.file_id,
        storage_alias=endpoint_alias,
        target_bucket_id=joint_fixture.bucket_id,
        target_object_id=object_id,
        decrypted_sha256=example_file.decrypted_sha256,
        context="unknown",
    )
    async with joint_fixture.kafka.expect_events(
        events=[
            ExpectedEvent(
                payload=download_served_event.model_dump(mode="json"),
                type_=joint_fixture.config.download_served_type,
            )
        ],
        in_topic=joint_fixture.config.download_served_topic,
    ):
        drs_object_response = await joint_fixture.rest_client.get(
            f"/objects/{accession}"
        )

    # Verify that the response contains the expected cache-control headers
    assert "Cache-Control" in drs_object_response.headers
    cache_headers = drs_object_response.headers["Cache-Control"]
    max_age_header = f"max-age={joint_fixture.config.presigned_url_expires_after}"
    assert cache_headers == f"{max_age_header}, private"

    # download file bytes:
    presigned_url = drs_object_response.json()["access_methods"][0]["access_url"]["url"]
    unintercepted_hosts.append(httpx.URL(presigned_url).host)
    downloaded_file = httpx.get(presigned_url, timeout=5)
    downloaded_file.raise_for_status()
    assert downloaded_file.content == file_object.content

    response = await joint_fixture.rest_client.get(
        f"/objects/{accession}/envelopes", timeout=5
    )
    assert response.status_code == status.HTTP_200_OK
    assert "Cache-Control" in response.headers
    assert response.headers["Cache-Control"] == "no-store"

    response = await joint_fixture.rest_client.get(
        "/objects/invalid_id/envelopes", timeout=5
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = await joint_fixture.rest_client.get(
        f"/objects/{accession}/envelopes",
        timeout=5,
        headers={"Authorization": "Bearer invalid"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_happy_deletion(
    populated_fixture: PopulatedFixture,
    tmp_file: FileObject,
    httpx_mock: HTTPXMock,  # noqa: F811
):
    """Simulates a typical, successful journey for file deletion."""
    joint_fixture = populated_fixture.joint_fixture

    # explicitly handle ekss API calls
    httpx_mock.add_callback(
        callback=router.handle_request,
        url=re.compile(rf"^{joint_fixture.config.ekss_base_url}.*"),
    )

    file_id = populated_fixture.example_file.file_id
    drs_object = await populated_fixture.mongodb_dao.get_by_id(file_id)
    object_id = str(drs_object.object_id)

    # place example content in the download bucket:
    file_object = tmp_file.model_copy(
        update={
            "bucket_id": joint_fixture.bucket_id,
            "object_id": object_id,
        }
    )
    await joint_fixture.s3.populate_file_objects(file_objects=[file_object])

    data_repository = joint_fixture.data_repository

    # request a stage to the outbox:
    async with joint_fixture.kafka.expect_events(
        events=[
            ExpectedEvent(
                payload={"file_id": file_id},
                type_=joint_fixture.config.file_deleted_type,
            )
        ],
        in_topic=joint_fixture.config.file_deleted_topic,
    ):
        await data_repository.delete_file(file_id=file_id)

    assert not await joint_fixture.s3.storage.does_object_exist(
        bucket_id=joint_fixture.bucket_id,
        object_id=object_id,
    )


async def test_bucket_cleanup(cleanup_fixture: CleanupFixture, caplog):
    """Test multiple download buckets cleanup handling."""
    bucket_cleaner = cleanup_fixture.bucket_cleaner

    await bucket_cleaner.cleanup_download_buckets(
        object_storages_config=cleanup_fixture.config
    )

    cached_id = cleanup_fixture.cached_file_id
    expired_id = cleanup_fixture.expired_file_id
    s3 = cleanup_fixture.s3

    # check if object within threshold is still there
    cached_object = await cleanup_fixture.mongodb_dao.get_by_id(cached_id)
    assert await s3.storage.does_object_exist(
        bucket_id=cleanup_fixture.bucket_id,
        object_id=str(cached_object.object_id),
    )

    # check if expired object has been removed from download bucket
    expired_object = await cleanup_fixture.mongodb_dao.get_by_id(expired_id)
    assert not await s3.storage.does_object_exist(
        bucket_id=cleanup_fixture.bucket_id,
        object_id=str(expired_object.object_id),
    )

    with caplog.at_level(logging.ERROR):
        await bucket_cleaner.cleanup_download_bucket(
            storage_alias=cleanup_fixture.endpoint_aliases.fake_node
        )

    expected_message = str(
        StorageAliasNotConfiguredError(alias=cleanup_fixture.endpoint_aliases.fake_node)
    )

    assert expected_message in caplog.records[0].message


async def test_bucket_cleanup_dangling_objects(cleanup_fixture: CleanupFixture, caplog):
    """Test that stale objects in the download bucket with no DB entry are handled.

    Also verifies that objects with DB entries are handled correctly: expired objects
    (last_accessed beyond the cache timeout) are removed, while objects within the
    threshold are left in place.
    """
    s3 = cleanup_fixture.s3
    bucket_id = cleanup_fixture.bucket_id
    bucket_cleaner = cleanup_fixture.bucket_cleaner
    storage_alias = cleanup_fixture.endpoint_aliases.valid_node
    timeout_days = cleanup_fixture.config.download_bucket_cache_timeout
    mongodb_dao = cleanup_fixture.mongodb_dao

    # Object with DB entry, within expiration threshold
    cached_object_id = uuid4()
    cached_db_entry = models.AccessTimeDrsObject(
        file_id=uuid4(),
        object_id=cached_object_id,
        decrypted_sha256="0" * 64,
        creation_date=now_utc_ms_prec(),
        decrypted_size=1,
        secret_id="cached-secret",
        encrypted_size=1,
        storage_alias=storage_alias,
        last_accessed=now_utc_ms_prec(),
    )
    await mongodb_dao.insert(cached_db_entry)
    with temp_file_object(bucket_id=bucket_id, object_id=str(cached_object_id)) as f:
        await s3.populate_file_objects([f])

    # Object with DB entry, beyond expiration threshold
    expired_object_id = uuid4()
    expired_db_entry = models.AccessTimeDrsObject(
        file_id=uuid4(),
        object_id=expired_object_id,
        decrypted_sha256="0" * 64,
        creation_date=now_utc_ms_prec(),
        decrypted_size=1,
        secret_id="expired-secret",
        encrypted_size=1,
        storage_alias=storage_alias,
        last_accessed=now_utc_ms_prec() - timedelta(days=timeout_days),
    )
    await mongodb_dao.insert(expired_db_entry)
    with temp_file_object(bucket_id=bucket_id, object_id=str(expired_object_id)) as f:
        await s3.populate_file_objects([f])

    # Object with no DB entry
    stale_object_id = uuid4()
    with temp_file_object(
        bucket_id=bucket_id,
        object_id=str(stale_object_id),
    ) as stale_file:
        await s3.populate_file_objects([stale_file])

    # first run without remove_dangling_objects
    with caplog.at_level(logging.WARNING):
        await bucket_cleaner.cleanup_download_buckets(
            object_storages_config=cleanup_fixture.config
        )

    expected_warning = str(
        bucket_cleaner.CleanupError(
            object_id=stale_object_id,
            storage_alias=storage_alias,
            reason="Object not found in database, skipping.",
        )
    )
    assert any(expected_warning in record.message for record in caplog.records)

    # only expired object must have been removed, cached and dangling remain
    assert await s3.storage.does_object_exist(
        bucket_id=bucket_id,
        object_id=str(cached_object_id),
    )
    assert not await s3.storage.does_object_exist(
        bucket_id=bucket_id,
        object_id=str(expired_object_id),
    )
    assert await s3.storage.does_object_exist(
        bucket_id=bucket_id,
        object_id=str(stale_object_id),
    )

    # second run with remove_dangling_objects
    await bucket_cleaner.cleanup_download_buckets(
        object_storages_config=cleanup_fixture.config,
        remove_dangling_objects=True,
    )

    # stale object must have been removed, cached object must still be in place
    assert not await s3.storage.does_object_exist(
        bucket_id=bucket_id,
        object_id=str(stale_object_id),
    )
    assert await s3.storage.does_object_exist(
        bucket_id=bucket_id,
        object_id=str(cached_object_id),
    )
