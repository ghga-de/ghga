# Copyright 2021 - 2022 Universität Tübingen, DKFZ and EMBL
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

"""Tests for the core functions of the cli"""

from filecmp import cmp
from os import path, remove

import pytest

from ghga_connector.core import check_url, download_file, upload_file

from ..fixtures import s3_fixture  # noqa: F401
from ..fixtures import state
from ..fixtures.utils import BASE_DIR

EXAMPLE_File = path.join(BASE_DIR.parent.parent.resolve(), "example_data/downloadable")


def teardown_module():
    """
    Delete the downloaded file
    """
    remove(EXAMPLE_File)


@pytest.mark.parametrize(
    "api_url,wait_time,expected_response",
    # Google has a higher availability than ghga.de
    [("https://www.google.de/", 1000, True), ("https://bad_url", 1000, False)],
)
def test_check_url(api_url, wait_time, expected_response):
    """
    Test the check_url function
    """
    response = check_url(api_url, wait_time)
    assert response == expected_response


def test_upload_file(
    s3_fixture,  # noqa F811
):
    """
    Test the upload_url function
    """

    uploadable_file = state.FILES["file_uploadable"]
    presigned_post = s3_fixture.storage.get_object_upload_url(
        bucket_id=uploadable_file.grouping_label,
        object_id=uploadable_file.file_id,
        expires_after=60,
    )
    upload_file(
        presigned_post=presigned_post,
        upload_file_path=str(uploadable_file.file_path.resolve()),
    )
    assert s3_fixture.storage.does_object_exist(
        bucket_id=uploadable_file.grouping_label,
        object_id=uploadable_file.file_id,
    )


def test_download_file(
    s3_fixture,  # noqa F811
):
    """
    Test the download_file function
    """

    downloadable_file = state.FILES["file_downloadable"]
    download_url = s3_fixture.storage.get_object_download_url(
        bucket_id=downloadable_file.grouping_label,
        object_id=downloadable_file.file_id,
        expires_after=60,
    )

    download_file(download_url, EXAMPLE_File)

    assert cmp(EXAMPLE_File, downloadable_file.file_path)
