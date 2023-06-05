# Copyright 2021 - 2023 Universität Tübingen, DKFZ, EMBL, and Universität zu Köln
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

from queue import Queue
from typing import Any, Iterator, Tuple, Union

import pytest

from ghga_connector.core.file_operations import (
    calc_part_ranges,
    download_content_range,
    download_file_parts,
)
from tests.fixtures.s3 import S3Fixture, get_big_s3_object, s3_fixture  # noqa: F401


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

    # donwload content range with dedicated function:
    download_content_range(download_url=download_url, start=start, end=end, queue=queue)

    obtained_start, obtained_bytes = queue.get()

    assert start == obtained_start
    assert expected_bytes == obtained_bytes


@pytest.mark.parametrize(
    "part_size",
    [5 * 1024 * 1024, 3 * 1024 * 1024, 1 * 1024 * 1024],
)
@pytest.mark.asyncio
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

    def url_generator() -> (
        Iterator[Union[Tuple[None, None, int], Tuple[str, int, None]]]
    ):
        while True:
            yield download_url, 0, None

    download_urls = url_generator()

    queue: Queue = Queue(maxsize=10)

    part_ranges = calc_part_ranges(part_size=part_size, total_file_size=total_file_size)

    # prepare kwargs:
    kwargs: dict[str, Any] = {
        "download_urls": download_urls,
        "queue": queue,
        "part_ranges": part_ranges,
        "max_concurrent_downloads": 5,
    }

    # donwload file parts with dedicated function:
    download_file_parts(**kwargs)

    obtained = 0
    while obtained < len(expected_bytes):
        start, obtained_bytes = queue.get()
        obtained += len(obtained_bytes)
        queue.task_done()
        assert expected_bytes[start : start + part_size] == obtained_bytes

    assert obtained == len(expected_bytes)
