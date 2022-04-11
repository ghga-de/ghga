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

"""Tests for the up- and download functions of the cli"""

from os import path

import pytest
import typer
from ghga_service_chassis_lib.s3 import ObjectStorageS3 as ObjectStorage

from ghga_connector.cli import (
    ApiNotReachable,
    DirectoryNotExist,
    MaxWaitTimeExceeded,
    download,
    upload,
)
from ghga_connector.core import (
    BadResponseCodeError,
    RequestFailedError,
    confirm_api_call,
)

from ..fixtures import s3_fixture  # noqa: F401
from ..fixtures import state
from ..fixtures.mock_api.testcontainer import MockAPIContainer
from ..fixtures.utils import BASE_DIR

EXAMPLE_FOLDER = path.join(BASE_DIR.parent.parent.resolve(), "example_data")


@pytest.mark.parametrize(
    "bad_url,file_id,output_dir,max_wait_time,expected_exception",
    [
        (True, "downloadable", EXAMPLE_FOLDER, "60", ApiNotReachable),
        (False, "downloadable", EXAMPLE_FOLDER, "60", None),
        (False, "not_downloadable", EXAMPLE_FOLDER, "60", BadResponseCodeError),
        (False, "retry", EXAMPLE_FOLDER, "60", MaxWaitTimeExceeded),
        (False, "downloadable", "/this_path/", "60", DirectoryNotExist),
    ],
)
def test_download(
    bad_url,
    file_id,
    output_dir,
    max_wait_time,
    expected_exception,
    s3_fixture,  # noqa F811
):
    """Test the download of a file, expects Abort, if the file was not found"""

    with MockAPIContainer(
        s3_download_url=get_presigned_download_url(s3_config=s3_fixture.config)
    ) as api:
        api_url = "http://bad_url" if bad_url else api.get_connection_url()

        try:
            download(
                api_url=api_url,
                file_id=file_id,
                output_dir=output_dir,
                max_wait_time=int(max_wait_time),
            )
            assert expected_exception is None
        except Exception as exception:
            assert isinstance(exception, expected_exception)


@pytest.mark.parametrize(
    "bad_url,file_id,file_path,expected_exception",
    [
        (
            True,
            "uploadable",
            EXAMPLE_FOLDER,
            typer.Abort,
        ),
        (False, "uploadable", path.join(EXAMPLE_FOLDER, "file1.test"), None),
        (False, "not_uploadable", path.join(EXAMPLE_FOLDER, "file2.test"), typer.Abort),
        (
            False,
            "1",
            "/this_path/does_not_exist.test",
            typer.Abort,
        ),
    ],
)
def test_upload(
    bad_url,
    file_id,
    file_path,
    expected_exception,
    s3_fixture,  # noqa F811
):
    """Test the upload of a file, expects Abort, if the file was not found"""

    with MockAPIContainer(
        s3_upload_url=get_presigned_upload_url(s3_config=s3_fixture.config)
    ) as api:
        api_url = "http://bad_url" if bad_url else api.get_connection_url()

        try:
            upload(api_url, file_id, file_path)
            assert expected_exception is None
        except Exception as exception:
            assert isinstance(exception, expected_exception)


@pytest.mark.parametrize(
    "bad_url,file_id,expected_exception",
    [
        (False, "uploaded", None),
        (False, "not_uploaded", BadResponseCodeError),
        (True, "uploaded", RequestFailedError),
    ],
)
def test_confirm_api_call(
    bad_url,
    file_id,
    expected_exception,
):
    """
    Test the confirm_api_call function
    """
    with MockAPIContainer() as api:
        api_url = "http://bad_url" if bad_url else api.get_connection_url()

        try:
            confirm_api_call(api_url=api_url, file_id=file_id)
            assert expected_exception is None
        except Exception as exception:
            assert isinstance(exception, expected_exception)


def get_presigned_download_url(s3_config) -> str:

    """
    Returns the presigned url for download
    """

    download_file = state.FILES["file_in_outbox"]

    with ObjectStorage(config=s3_config) as storage:
        download_url = storage.get_object_download_url(
            bucket_id=download_file.grouping_label,
            object_id=download_file.file_id,
            expires_after=60,
        )

    return download_url


def get_presigned_upload_url(s3_config) -> str:  # noqa F811

    """
    Returns the presigned url for upload
    """

    upload_file = state.FILES["file_can_be_uploaded"]

    with ObjectStorage(config=s3_config) as storage:
        upload_url = storage.get_object_upload_url(
            bucket_id=upload_file.grouping_label,
            object_id=upload_file.file_id,
            expires_after=60,
        )

    return upload_url
