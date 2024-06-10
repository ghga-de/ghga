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

"""Test file operations"""

from collections.abc import Iterator
from queue import Empty, Queue
from typing import Any
from unittest.mock import Mock

import pytest

from ghga_connector.core.api_calls import WorkPackageAccessor
from ghga_connector.core.client import httpx_client
from ghga_connector.core.downloading import Downloader
from ghga_connector.core.downloading.structs import URLResponse
from ghga_connector.core.file_operations import calc_part_ranges
from tests.fixtures.s3 import (  # noqa: F401
    S3Fixture,
    get_big_s3_object,
    reset_state,
    s3_fixture,
)


@pytest.mark.parametrize(
    "start, end, file_size",
    [
        (0, 20 * 1024 * 1024 - 1, 20 * 1024 * 1024),  # download full file as one part
        (  # download intermediate part:
            5 * 1024 * 1024,
            10 * 1024 * 1024 - 1,
            20 * 1024 * 1024,
        ),
    ],
)
@pytest.mark.asyncio
async def test_download_content_range(
    start: int,
    end: int,
    file_size: int,
    s3_fixture: S3Fixture,  # noqa: F811
):
    """Test the `download_content_range` function."""
    # prepare state and the expected result:
    big_object = await get_big_s3_object(s3_fixture, object_size=file_size)
    download_url = await s3_fixture.storage.get_object_download_url(
        object_id=big_object.object_id, bucket_id=big_object.bucket_id
    )
    expected_bytes = big_object.content[start : end + 1]

    queue: Queue = Queue(maxsize=10)

    # download content range with dedicated function:
    with httpx_client() as client:
        # no work package accessor calls in download_content_range, just mock for correct type
        dummy_accessor = Mock(spec=WorkPackageAccessor)
        downloader = Downloader(
            file_id=big_object.object_id,
            work_package_accessor=dummy_accessor,
            client=client,
        )
        downloader.download_content_range(
            download_url=download_url, start=start, end=end, queue=queue
        )

    obtained_start, obtained_bytes = queue.get()

    assert start == obtained_start
    assert expected_bytes == obtained_bytes


@pytest.mark.parametrize(
    "part_size",
    [5 * 1024 * 1024, 3 * 1024 * 1024, 1 * 1024 * 1024],
)
@pytest.mark.asyncio(scope="session")
async def test_download_file_parts(
    part_size: int,
    s3_fixture: S3Fixture,  # noqa: F811
):
    """Test the `download_file_parts` function."""
    # prepare state and the expected result:
    big_object = await get_big_s3_object(s3_fixture)
    total_file_size = len(big_object.content)
    expected_bytes = big_object.content

    download_url = await s3_fixture.storage.get_object_download_url(
        object_id=big_object.object_id, bucket_id=big_object.bucket_id
    )

    def url_generator() -> Iterator[URLResponse]:
        while True:
            yield URLResponse(download_url=download_url, file_size=0)

    url_responses = url_generator()

    queue: Queue = Queue(maxsize=10)

    part_ranges = calc_part_ranges(part_size=part_size, total_file_size=total_file_size)

    with httpx_client() as client:
        # prepare kwargs:
        kwargs: dict[str, Any] = {
            "url_response": url_responses,
            "queue": queue,
            "part_ranges": part_ranges,
            "max_concurrent_downloads": 5,
        }

        # no work package accessor calls in download_file_parts, just mock for correct type
        dummy_accessor = Mock(spec=WorkPackageAccessor)
        downloader = Downloader(
            file_id=big_object.object_id,
            work_package_accessor=dummy_accessor,
            client=client,
        )
        # download file parts with dedicated function:
        downloader.download_file_parts(**kwargs)

        obtained = 0
        while obtained < len(expected_bytes):
            try:
                start, obtained_bytes = queue.get(block=False)
            except Empty:
                continue
            obtained += len(obtained_bytes)
            queue.task_done()
            assert expected_bytes[start : start + part_size] == obtained_bytes

        assert obtained == len(expected_bytes)
