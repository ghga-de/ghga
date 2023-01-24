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

from typing import Optional

import pytest

from ghga_connector.core.file_operations import (
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
def test_download_content_range(
    start: int,
    end: int,
    file_size: int,
    s3_fixture: S3Fixture,  # noqa: F811
):
    """Test the `download_content_range` function."""
    # prepare state and the expected result:
    big_object = get_big_s3_object(s3_fixture, object_size=file_size)
    download_url = s3_fixture.storage.get_object_download_url(
        object_id=big_object.object_id, bucket_id=big_object.bucket_id
    )
    expected_bytes = big_object.content[start : end + 1]

    # donwload content range with dedicated function:
    obtained_bytes = download_content_range(
        download_url=download_url, start=start, end=end
    )

    assert expected_bytes == obtained_bytes


@pytest.mark.parametrize(
    "from_part",
    [None, 3],
)
def test_download_file_parts(
    from_part: Optional[int],
    s3_fixture: S3Fixture,  # noqa: F811
):
    """Test the `download_file_parts` function."""
    # prepare state and the expected result:
    part_size = 5 * 1024 * 1024
    big_object = get_big_s3_object(s3_fixture)
    total_file_size = len(big_object.content)
    if from_part is not None:
        offset = (from_part - 1) * part_size
        expected_bytes = big_object.content[offset:total_file_size]
    else:
        expected_bytes = big_object.content

    download_url = s3_fixture.storage.get_object_download_url(
        object_id=big_object.object_id, bucket_id=big_object.bucket_id
    )

    # prepare kwargs:
    kwargs = {
        "download_url": download_url,
        "part_size": part_size,
        "total_file_size": total_file_size,
    }
    if from_part is not None:
        kwargs["from_part"] = from_part

    # donwload file parts with dedicated function:
    obtained_bytes = bytes()
    for part in download_file_parts(**kwargs):
        obtained_bytes += part

    assert expected_bytes == obtained_bytes
